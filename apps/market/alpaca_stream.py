import logging
import time
import threading
import datetime
from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from decouple import config
from django.db import transaction
from django.utils import timezone

from apps.market.utils import push_market_update

logger = logging.getLogger(__name__)

ACTIVE_SYMBOL_POLL_SECONDS = 2


class AlpacaStreamManager:
    def __init__(self):
        self.api_key = config("ALPACA_API_KEY", default="")
        self.secret_key = config("ALPACA_SECRET_KEY", default="")

    def get_symbols(self) -> list[str]:
        from apps.tickers.models import Ticker

        return list(Ticker.objects.values_list("symbol", flat=True))

    def get_active_symbols(self) -> list[str]:
        from apps.market.models import ActiveMarketSubscription

        now = timezone.now()
        ActiveMarketSubscription.objects.filter(expires_at__lt=now).delete()
        return list(
            ActiveMarketSubscription.objects
            .filter(expires_at__gte=now)
            .values_list("symbol", flat=True)
            .distinct()
            .order_by("symbol")
        )

    @staticmethod
    def _trade_attr(trade, name: str, default=None):
        if isinstance(trade, dict):
            return trade.get(name, default)
        return getattr(trade, name, default)

    @staticmethod
    def _as_decimal(value) -> Decimal | None:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def _minute_bucket(ts):
        if ts is None:
            ts = timezone.now()
        if timezone.is_naive(ts):
            ts = timezone.make_aware(ts, datetime.timezone.utc)
        return ts.replace(second=0, microsecond=0)

    def _store_trade_and_bar(self, trade):
        from apps.market.models import PriceSnapshot, TradeTick
        from apps.tickers.models import Ticker

        symbol = str(self._trade_attr(trade, "symbol", "")).upper()
        price = self._as_decimal(self._trade_attr(trade, "price"))
        if not symbol or price is None:
            return None

        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return None

        size = int(self._trade_attr(trade, "size", 0) or 0)
        timestamp = self._trade_attr(trade, "timestamp", None) or timezone.now()
        exchange = str(self._trade_attr(trade, "exchange", "") or "")
        trade_id = str(
            self._trade_attr(trade, "id", None)
            or self._trade_attr(trade, "trade_id", "")
            or ""
        )
        conditions = self._trade_attr(trade, "conditions", []) or []
        if not isinstance(conditions, list):
            conditions = list(conditions) if isinstance(conditions, tuple) else [str(conditions)]

        bar_timestamp = self._minute_bucket(timestamp)
        with transaction.atomic():
            TradeTick.objects.create(
                ticker=ticker,
                price=price,
                size=size,
                exchange=exchange,
                trade_id=trade_id,
                conditions=conditions,
                timestamp=timestamp,
            )

            snapshot = (
                PriceSnapshot.objects
                .select_for_update()
                .filter(
                    ticker=ticker,
                    timestamp=bar_timestamp,
                    source=PriceSnapshot.SOURCE_ALPACA_STREAM,
                )
                .first()
            )
            if snapshot is None:
                snapshot = PriceSnapshot.objects.create(
                    ticker=ticker,
                    price=price,
                    open_price=price,
                    high_price=price,
                    low_price=price,
                    volume=size,
                    timestamp=bar_timestamp,
                    source=PriceSnapshot.SOURCE_ALPACA_STREAM,
                )
            else:
                snapshot.price = price
                snapshot.high_price = max(snapshot.high_price or price, price)
                snapshot.low_price = min(snapshot.low_price or price, price)
                snapshot.volume = (snapshot.volume or 0) + size
                snapshot.save(update_fields=["price", "high_price", "low_price", "volume"])

        return {
            "symbol": symbol,
            "price": price,
            "size": size,
            "exchange": exchange,
            "trade_id": trade_id,
            "conditions": conditions,
            "timestamp": timestamp,
            "bar": snapshot,
        }

    async def handle_trade(self, trade) -> None:
        """Called by Alpaca SDK for every trade tick received."""
        try:
            stored = await sync_to_async(self._store_trade_and_bar, thread_sensitive=False)(trade)
            if stored is None:
                return

            bar = stored["bar"]
            symbol = stored["symbol"]
            payload = {
                "type": "trade",
                "symbol": symbol,
                "price": str(stored["price"]),
                "size": stored["size"],
                "exchange": stored["exchange"],
                "trade_id": stored["trade_id"],
                "conditions": stored["conditions"],
                "trade_timestamp": stored["timestamp"].isoformat(),
                "timestamp": stored["timestamp"].isoformat(),
                "bar_timestamp": bar.timestamp.isoformat(),
                "open": str(bar.open_price),
                "high": str(bar.high_price),
                "low": str(bar.low_price),
                "close": str(bar.price),
                "volume": bar.volume,
            }
            await sync_to_async(push_market_update, thread_sensitive=False)(symbol, payload)

        except Exception as e:
            logger.error("Error storing trade tick: %s", e)

    async def handle_bar(self, bar) -> None:
        """Called by Alpaca SDK for each price bar received (must be async)."""
        from apps.market.models import PriceSnapshot
        from apps.tickers.models import Ticker

        try:
            ticker = await sync_to_async(Ticker.objects.get)(symbol=bar.symbol)
        except Ticker.DoesNotExist:
            return

        try:
            await sync_to_async(PriceSnapshot.objects.create)(
                ticker=ticker,
                price=bar.close,
                open_price=bar.open,
                high_price=bar.high,
                low_price=bar.low,
                volume=bar.volume,
                timestamp=bar.timestamp,
                source=PriceSnapshot.SOURCE_ALPACA_STREAM,
            )

            await sync_to_async(push_market_update)(
                bar.symbol,
                {
                    "type": "price",
                    "open": str(bar.open),
                    "high": str(bar.high),
                    "low": str(bar.low),
                    "price": str(bar.close),
                    "volume": bar.volume,
                    "timestamp": bar.timestamp.isoformat(),
                },
            )

        except Exception as e:
            logger.error("Error storing bar for %s: %s", bar.symbol, e)

    def run(self) -> None:
        """Run the Alpaca trade stream with auto-reconnect and active symbol polling."""
        from alpaca.data.live import StockDataStream

        backoff = 10
        while True:
            symbols = self.get_active_symbols()
            if not symbols:
                logger.info("No visible market charts. Waiting for active subscriptions.")
                time.sleep(ACTIVE_SYMBOL_POLL_SECONDS)
                continue
            try:
                stream = StockDataStream(self.api_key, self.secret_key)
                subscribed = set(symbols)
                stream.subscribe_trades(self.handle_trade, *symbols)

                stop_monitor = threading.Event()

                def monitor_symbols():
                    nonlocal subscribed
                    while not stop_monitor.is_set():
                        try:
                            active = set(self.get_active_symbols())
                            additions = sorted(active - subscribed)
                            removals = sorted(subscribed - active)
                            if additions:
                                stream.subscribe_trades(self.handle_trade, *additions)
                                logger.info("Subscribed live trades for: %s", additions)
                            if removals:
                                stream.unsubscribe_trades(*removals)
                                logger.info("Unsubscribed live trades for: %s", removals)
                            subscribed = active
                        except Exception as exc:
                            logger.error("Active symbol monitor failed: %s", exc)
                        stop_monitor.wait(ACTIVE_SYMBOL_POLL_SECONDS)

                monitor = threading.Thread(target=monitor_symbols, daemon=True)
                monitor.start()
                logger.info("Alpaca trade stream started for: %s", symbols)
                stream.run()
                stop_monitor.set()
                backoff = 10  # reset on clean exit
            except Exception as e:
                try:
                    stop_monitor.set()
                except UnboundLocalError:
                    pass
                msg = str(e).lower()
                if "connection limit" in msg or "429" in msg:
                    logger.warning(
                        "Alpaca connection limit hit. Waiting %ss before retry.", backoff
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, 120)
                else:
                    logger.error("Alpaca stream error: %s. Reconnecting in 10s.", e)
                    backoff = 10
                    time.sleep(10)

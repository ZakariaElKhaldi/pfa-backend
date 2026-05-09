import logging
import time

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from decouple import config

logger = logging.getLogger(__name__)


class AlpacaStreamManager:
    def __init__(self):
        self.api_key = config("ALPACA_API_KEY", default="")
        self.secret_key = config("ALPACA_SECRET_KEY", default="")

    def get_symbols(self) -> list[str]:
        from apps.tickers.models import Ticker

        return list(Ticker.objects.values_list("symbol", flat=True))

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
            )

            channel_layer = get_channel_layer()
            if channel_layer:
                await channel_layer.group_send(
                    f"market_{bar.symbol}",
                    {
                        "type": "market.update",
                        "data": {
                            "type": "price",
                            "open": str(bar.open),
                            "high": str(bar.high),
                            "low": str(bar.low),
                            "price": str(bar.close),
                            "volume": bar.volume,
                            "timestamp": bar.timestamp.isoformat(),
                        },
                    },
                )

            from apps.events.bus import publish
            from apps.events.types import PRICE_UPDATED

            await sync_to_async(publish)(PRICE_UPDATED, {
                "ticker": bar.symbol,
                "price": str(bar.close),
                "volume": bar.volume,
                "timestamp": bar.timestamp.isoformat(),
            })
        except Exception as e:
            logger.error("Error storing bar for %s: %s", bar.symbol, e)

    def run(self) -> None:
        """Run the Alpaca stream with auto-reconnect and exponential backoff."""
        from alpaca.data.live import StockDataStream

        backoff = 10
        while True:
            symbols = self.get_symbols()
            if not symbols:
                logger.info("No tickers tracked. Waiting 60s before retrying.")
                time.sleep(60)
                continue
            try:
                stream = StockDataStream(self.api_key, self.secret_key)
                stream.subscribe_bars(self.handle_bar, *symbols)
                logger.info("Alpaca stream started for: %s", symbols)
                stream.run()
                backoff = 10  # reset on clean exit
            except Exception as e:
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

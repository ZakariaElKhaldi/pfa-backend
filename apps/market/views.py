import datetime

from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import ScopedAPIKeyPermission, ScopedUserPermission

from .models import PriceSnapshot
from .serializers import PriceSnapshotSerializer
from .indicators import (
    sma, ema, rsi, bollinger_bands, macd, historical_volatility,
)
from django.utils import timezone
from decouple import config


QUOTE_STALE_MINUTES = 15
PRICE_HISTORY_LIMIT = 100


def _fetch_and_store_latest_bar(symbol: str):
    from alpaca.data import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestBarRequest
    from apps.tickers.models import Ticker

    api_key = config("ALPACA_API_KEY", default="")
    secret_key = config("ALPACA_SECRET_KEY", default="")
    if not api_key or not secret_key:
        return None

    client = StockHistoricalDataClient(api_key, secret_key)
    bars = client.get_stock_latest_bar(StockLatestBarRequest(symbol_or_symbols=[symbol]))
    bar = bars.get(symbol)
    if bar is None:
        return None

    try:
        ticker = Ticker.objects.get(symbol=symbol)
    except Ticker.DoesNotExist:
        return None

    return PriceSnapshot.objects.create(
        ticker=ticker,
        price=bar.close,
        open_price=bar.open,
        high_price=bar.high,
        low_price=bar.low,
        volume=bar.volume,
        timestamp=bar.timestamp if bar.timestamp else timezone.now(),
        source=PriceSnapshot.SOURCE_ALPACA_REST,
    )


def _fetch_and_store_recent_bars(symbol: str, limit: int = PRICE_HISTORY_LIMIT) -> int:
    from alpaca.data import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    from apps.tickers.models import Ticker

    api_key = config("ALPACA_API_KEY", default="")
    secret_key = config("ALPACA_SECRET_KEY", default="")
    if not api_key or not secret_key:
        return 0

    try:
        ticker = Ticker.objects.get(symbol=symbol)
    except Ticker.DoesNotExist:
        return 0

    client = StockHistoricalDataClient(api_key, secret_key)
    request = StockBarsRequest(
        symbol_or_symbols=[symbol],
        timeframe=TimeFrame.Minute,
        start=timezone.now() - datetime.timedelta(days=7),
        limit=limit,
    )
    bar_set = client.get_stock_bars(request)
    bars_by_symbol = getattr(bar_set, "data", None) or bar_set
    bars = bars_by_symbol.get(symbol, []) if hasattr(bars_by_symbol, "get") else []

    created = 0
    for bar in bars[-limit:]:
        timestamp = bar.timestamp if bar.timestamp else timezone.now()
        exists = PriceSnapshot.objects.filter(
            ticker=ticker,
            timestamp=timestamp,
            source=PriceSnapshot.SOURCE_ALPACA_REST,
        ).exists()
        if exists:
            continue
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=bar.close,
            open_price=bar.open,
            high_price=bar.high,
            low_price=bar.low,
            volume=bar.volume,
            timestamp=timestamp,
            source=PriceSnapshot.SOURCE_ALPACA_REST,
        )
        created += 1
    return created


class TickerPriceListView(generics.ListAPIView):
    serializer_class = PriceSnapshotSerializer
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["market.read"]

    def get_queryset(self):
        symbol = self.kwargs["symbol"].upper()
        qs = PriceSnapshot.objects.filter(
            ticker__symbol=symbol,
            source__in=PriceSnapshot.LIVE_SOURCES,
        )
        if not qs.exists():
            try:
                _fetch_and_store_recent_bars(symbol)
            except Exception:
                pass
        return (
            PriceSnapshot.objects
            .filter(ticker__symbol=symbol, source__in=PriceSnapshot.LIVE_SOURCES)
            .order_by("-timestamp")[:100]
        )


class TickerIndicatorsView(APIView):
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["market.read"]

    def get(self, request, symbol):
        prices_qs = PriceSnapshot.objects.filter(
            ticker__symbol=symbol.upper(),
            source__in=PriceSnapshot.LIVE_SOURCES,
        ).order_by("timestamp").values_list("price", flat=True)
        close_prices = [float(p) for p in prices_qs]

        if not close_prices:
            return Response(
                {"detail": "No price data."}, status=status.HTTP_404_NOT_FOUND
            )

        bb = bollinger_bands(close_prices, 20)
        macd_result = macd(close_prices)

        return Response({
            "symbol": symbol,
            "close": close_prices[-1],
            "sma_20": sma(close_prices, 20),
            "ema_12": ema(close_prices, 12),
            "rsi_14": rsi(close_prices, 14),
            "bollinger_bands": bb,
            "macd": macd_result,
            "volatility": historical_volatility(close_prices, 20),
        })


class TickerQuoteView(APIView):
    """Returns the single most recent PriceSnapshot for a ticker."""
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["market.read"]

    def get(self, request, symbol):
        symbol = symbol.upper()
        snap = (
            PriceSnapshot.objects
            .filter(
                ticker__symbol=symbol,
                source__in=PriceSnapshot.LIVE_SOURCES,
            )
            .order_by("-timestamp")
            .first()
        )
        if snap is None or snap.timestamp < timezone.now() - datetime.timedelta(minutes=QUOTE_STALE_MINUTES):
            try:
                fresh_snap = _fetch_and_store_latest_bar(symbol)
            except Exception:
                fresh_snap = None
            if fresh_snap is not None:
                snap = fresh_snap
        if snap is None:
            return Response({"detail": "No price data."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PriceSnapshotSerializer(snap).data)


class MarketClockView(APIView):
    permission_classes = [IsAuthenticated, ScopedAPIKeyPermission, ScopedUserPermission]
    required_scopes = ["market.read"]

    def get(self, request):
        from alpaca.trading.client import TradingClient

        api_key = config("ALPACA_API_KEY", default="")
        secret_key = config("ALPACA_SECRET_KEY", default="")
        if not api_key or not secret_key:
            return Response(
                {"detail": "Alpaca credentials are not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            clock = TradingClient(api_key=api_key, secret_key=secret_key, paper=True).get_clock()
        except Exception as exc:
            return Response(
                {"detail": f"Failed to fetch market clock: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "is_open": bool(clock.is_open),
                "next_open": clock.next_open.isoformat(),
                "next_close": clock.next_close.isoformat(),
                "server_timestamp": clock.timestamp.isoformat(),
            }
        )

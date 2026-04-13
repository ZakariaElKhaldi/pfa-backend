from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PriceSnapshot
from .serializers import PriceSnapshotSerializer
from .indicators import (
    sma, ema, rsi, bollinger_bands, macd, historical_volatility,
)


class TickerPriceListView(generics.ListAPIView):
    serializer_class = PriceSnapshotSerializer

    def get_queryset(self):
        return PriceSnapshot.objects.filter(ticker__symbol=self.kwargs["symbol"]).order_by(
            "-timestamp"
        )[:100]


class TickerIndicatorsView(APIView):
    def get(self, request, symbol):
        prices_qs = PriceSnapshot.objects.filter(
            ticker__symbol=symbol
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

    def get(self, request, symbol):
        snap = (
            PriceSnapshot.objects
            .filter(ticker__symbol=symbol.upper())
            .order_by("-timestamp")
            .first()
        )
        if snap is None:
            return Response({"detail": "No price data."}, status=status.HTTP_404_NOT_FOUND)
        return Response(PriceSnapshotSerializer(snap).data)

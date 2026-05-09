from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAnalystOrAdmin

from . import services
from .models import BacktestRun
from .serializers import BacktestRequestSerializer, BacktestRunSerializer
from .throttles import BacktestThrottle

import logging

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from collections import defaultdict

from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from . import timesfm_service

logger = logging.getLogger(__name__)


class TopMoversView(APIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        try:
            window = services.parse_window(request.query_params.get("window", "24h"))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        try:
            limit = max(1, min(int(request.query_params.get("limit", 10)), 100))
        except (TypeError, ValueError):
            return Response({"detail": "limit must be an integer"}, status=400)
        direction = request.query_params.get("direction", "both")
        if direction not in ("both", "up", "down"):
            return Response({"detail": "direction must be both|up|down"}, status=400)
        return Response(services.compute_top_movers(window, limit, direction))


class SentimentLeaderboardView(APIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        try:
            window = services.parse_window(request.query_params.get("window", "24h"))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        try:
            limit = max(1, min(int(request.query_params.get("limit", 20)), 100))
        except (TypeError, ValueError):
            return Response({"detail": "limit must be an integer"}, status=400)
        return Response(services.compute_sentiment_leaderboard(window, limit))


class CorrelationView(APIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        symbols_raw = request.query_params.get("symbols", "")
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        try:
            window = services.parse_window(request.query_params.get("window", "30d"))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        metric = request.query_params.get("metric", "price")
        try:
            return Response(services.compute_correlation_matrix(symbols, window, metric))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)


class SectorRollupView(APIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        try:
            window = services.parse_window(request.query_params.get("window", "24h"))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(services.compute_sector_rollup(window))


class SignalHeatmapView(APIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    def get(self, request):
        symbols_raw = request.query_params.get("symbols", "")
        symbols = [s.strip().upper() for s in symbols_raw.split(",") if s.strip()]
        if not symbols:
            return Response({"detail": "symbols query param required"}, status=400)
        try:
            window = services.parse_window(request.query_params.get("window", "7d"))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        try:
            return Response(services.compute_signal_heatmap(symbols, window))
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)


class BacktestRunListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]
    serializer_class = BacktestRunSerializer

    def get_queryset(self):
        return BacktestRun.objects.filter(user=self.request.user).select_related("ticker")

    def get_throttles(self):
        if self.request.method == "POST":
            return [BacktestThrottle()]
        return []

    def create(self, request, *args, **kwargs):
        serializer = BacktestRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            run = services.run_backtest(
                user=request.user,
                symbol=serializer.validated_data["symbol"],
                start=serializer.validated_data["start"],
                end=serializer.validated_data["end"],
                strategy=serializer.validated_data["strategy"],
                params=serializer.validated_data.get("params", {}),
            )
        except ValueError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(BacktestRunSerializer(run).data, status=201)


class BacktestRunDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]
    serializer_class = BacktestRunSerializer

    def get_queryset(self):
        return BacktestRun.objects.filter(user=self.request.user)


class VolumeForecastView(APIView):
    """30-day volume forecast powered by Google TimesFM."""

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    @method_decorator(cache_page(60 * 60 * 12))  # 12-hour cache per ticker
    def get(self, request):
        ticker = request.query_params.get("ticker", "").upper()
        if not ticker:
            return Response({"detail": "ticker parameter is required"}, status=400)

        # Fetch latest 200 volume records directly in SQL (desc → reverse)
        volume_qs = (
            PriceSnapshot.objects
            .filter(ticker__symbol=ticker)
            .order_by("-timestamp")
            .values_list("volume", flat=True)[:200]
        )
        # Reverse to oldest-first for the model
        volume_history = list(reversed(list(volume_qs)))

        if len(volume_history) < 10:
            return Response(
                {"detail": "Not enough historical volume data for forecasting."},
                status=400,
            )

        try:
            forecasts = timesfm_service.forecast_volume(volume_history, horizon=30)
        except Exception:
            logger.exception("TimesFM inference failed for %s", ticker)
            return Response(
                {"detail": "Model inference failed. Please try again later."},
                status=500,
            )

        return Response({
            "ticker": ticker,
            "horizon": len(forecasts),
            "forecast": forecasts,
        })


class BreadthForecastView(APIView):
    """30-day market breadth (A/D line) forecast powered by Google TimesFM."""

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    @method_decorator(cache_page(60 * 60 * 12))  # 12-hour cache
    def get(self, request):
        # We need historical sequence. Fetch recent signals to build a decent breadth line
        signals = SignalSnapshot.objects.all().order_by('-created_at')[:3000]
        
        # Group by day
        by_day = defaultdict(lambda: {"BUY": 0, "SELL": 0})
        for s in signals:
            day_str = s.created_at.strftime("%Y-%m-%d")
            if s.signal == "BUY":
                by_day[day_str]["BUY"] += 1
            elif s.signal == "SELL":
                by_day[day_str]["SELL"] += 1
                
        if len(by_day) < 10:
            return Response(
                {"detail": "Not enough historical breadth data for forecasting."},
                status=400,
            )
            
        # Sort by date
        sorted_days = sorted(by_day.items())
        
        # Build cumulative breadth series
        cumulative = 0
        breadth_history = []
        for date_str, counts in sorted_days:
            net = counts["BUY"] - counts["SELL"]
            cumulative += net
            breadth_history.append(cumulative)
            
        try:
            # We can reuse the timesfm_service which just expects a sequence of numbers
            forecasts = timesfm_service.forecast_series(breadth_history, horizon=30, clip_zero=False)
        except Exception:
            logger.exception("TimesFM inference failed for Market Breadth")
            return Response(
                {"detail": "Model inference failed. Please try again later."},
                status=500,
            )

        return Response({
            "horizon": len(forecasts),
            "forecast": forecasts,
            "last_historical_value": breadth_history[-1],
        })


import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAnalystOrAdmin
from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot

from . import services, timesfm_service
from .models import BacktestRun
from .serializers import BacktestRequestSerializer, BacktestRunSerializer
from .throttles import BacktestThrottle

logger = logging.getLogger(__name__)

BREADTH_WINDOWS = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}
VOLUME_FORECAST_CACHE_TTL_SECONDS = 60 * 60 * 12


def _is_timesfm_unavailable(exc):
    return (
        isinstance(exc, timesfm_service.TimesFMUnavailableError)
        or exc.__class__.__name__ == "TimesFMUnavailableError"
    )


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

    def get(self, request):
        ticker = request.query_params.get("ticker", "").upper()
        if not ticker:
            return Response({"detail": "ticker parameter is required"}, status=400)
        cache_key = f"analytics:volume_forecast:v1:{ticker}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        # Fetch latest 200 volume records directly in SQL (desc → reverse)
        volume_qs = (
            PriceSnapshot.objects
            .filter(
                ticker__symbol=ticker,
                source__in=PriceSnapshot.LIVE_SOURCES,
            )
            .order_by("-timestamp")
            .values_list("volume", flat=True)[:200]
        )
        # Reverse to oldest-first for the model
        volume_history = list(reversed(list(volume_qs)))

        if len(volume_history) < 10:
            return Response(
                {
                    "detail": "Not enough historical volume data for forecasting.",
                    "code": "INSUFFICIENT_HISTORY",
                },
                status=400,
            )

        try:
            timesfm_service.check_timesfm_ready()
            forecasts = timesfm_service.forecast_volume(volume_history, horizon=30)
        except Exception as exc:
            if _is_timesfm_unavailable(exc):
                return Response(
                    {
                        "detail": "Forecast model is temporarily unavailable.",
                        "code": "TIMESFM_UNAVAILABLE",
                        "method": "timesfm",
                        "model_status": "TIMESFM_UNAVAILABLE",
                    },
                    status=503,
                )
            if isinstance(exc, ValueError):
                return Response(
                    {"detail": str(exc), "code": "INSUFFICIENT_HISTORY"},
                    status=400,
                )
            logger.exception("TimesFM inference failed for %s", ticker)
            return Response(
                {
                    "detail": "Model inference failed. Please try again later.",
                    "code": "FORECAST_INFERENCE_FAILED",
                },
                status=500,
            )

        payload = {
            "ticker": ticker,
            "horizon": len(forecasts),
            "forecast": forecasts,
            "method": "timesfm",
            "model_status": "ready",
        }
        # Cache only successful forecasts. Transient failures should recover immediately.
        cache.set(cache_key, payload, VOLUME_FORECAST_CACHE_TTL_SECONDS)
        return Response(payload)


class BreadthForecastView(APIView):
    """30-day market breadth (A/D line) forecast powered by Google TimesFM."""

    permission_classes = [IsAuthenticated, IsAnalystOrAdmin]

    @method_decorator(cache_page(60 * 60 * 12))  # 12-hour cache
    def get(self, request):
        window = request.query_params.get("window", "7d").lower()
        if window not in BREADTH_WINDOWS:
            return Response({"detail": "window must be one of 1d, 7d, 30d, 90d"}, status=400)

        since = timezone.now() - BREADTH_WINDOWS[window]
        trunc = TruncHour("created_at") if window == "1d" else TruncDate("created_at")
        rows = (
            SignalSnapshot.objects
            .filter(created_at__gte=since)
            .annotate(bucket=trunc)
            .values("bucket")
            .annotate(
                buy=Count("id", filter=Q(signal=SignalSnapshot.SIGNAL_BUY)),
                sell=Count("id", filter=Q(signal=SignalSnapshot.SIGNAL_SELL)),
                hold=Count("id", filter=Q(signal=SignalSnapshot.SIGNAL_HOLD)),
            )
            .order_by("bucket")
        )

        cumulative = 0
        history = []
        for row in rows:
            net = row["buy"] - row["sell"]
            cumulative += net
            bucket = row["bucket"]
            history.append({
                "bucket": bucket.isoformat(),
                "buy": row["buy"],
                "sell": row["sell"],
                "hold": row["hold"],
                "net": net,
                "cumulative": cumulative,
            })

        if len(history) < 2:
            return Response(
                {
                    "detail": "Not enough historical breadth data for forecasting.",
                    "code": "INSUFFICIENT_HISTORY",
                    "history": history,
                },
                status=400,
            )

        breadth_history = [point["cumulative"] for point in history]
            
        try:
            timesfm_service.check_timesfm_ready()
            # We can reuse the timesfm_service which just expects a sequence of numbers
            forecasts = timesfm_service.forecast_series(
                breadth_history,
                horizon=30,
                clip_zero=False,
            )
        except Exception as exc:
            if _is_timesfm_unavailable(exc):
                return Response(
                    {
                        "detail": "Forecast model is temporarily unavailable.",
                        "code": "TIMESFM_UNAVAILABLE",
                        "history": history,
                        "forecast": [],
                        "last_historical_value": breadth_history[-1],
                        "method": "timesfm",
                        "model_status": "TIMESFM_UNAVAILABLE",
                    },
                    status=503,
                )
            if isinstance(exc, ValueError):
                return Response(
                    {"detail": str(exc), "code": "INSUFFICIENT_HISTORY", "history": history},
                    status=400,
                )
            logger.exception("TimesFM inference failed for Market Breadth")
            return Response(
                {
                    "detail": "Model inference failed. Please try again later.",
                    "code": "FORECAST_INFERENCE_FAILED",
                },
                status=500,
            )

        return Response({
            "history": history,
            "horizon": len(forecasts),
            "forecast": forecasts,
            "last_historical_value": breadth_history[-1],
            "method": "timesfm",
            "model_status": "ready",
        })

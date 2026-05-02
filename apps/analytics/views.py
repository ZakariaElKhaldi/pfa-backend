from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAnalystOrAdmin

from . import services
from .models import BacktestRun
from .serializers import BacktestRequestSerializer, BacktestRunSerializer
from .throttles import BacktestThrottle


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

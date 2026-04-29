from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAnalystOrAdmin

from . import services


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

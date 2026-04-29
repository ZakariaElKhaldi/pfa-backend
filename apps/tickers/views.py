from rest_framework import filters, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.intelligence.models import MarketMoodSnapshot

from .models import Ticker, Watchlist
from .serializers import TickerSerializer, WatchlistSerializer


class TickerListCreateView(generics.ListCreateAPIView):
    queryset = Ticker.objects.all().order_by("symbol")
    serializer_class = TickerSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["symbol", "name"]


class TickerDetailView(generics.RetrieveDestroyAPIView):
    queryset = Ticker.objects.all()
    serializer_class = TickerSerializer
    lookup_field = "symbol"


class WatchlistListCreateView(APIView):
    def get(self, request):
        items = Watchlist.objects.filter(user=request.user).select_related("ticker")
        return Response(WatchlistSerializer(items, many=True).data)

    def post(self, request):
        symbol = request.data.get("symbol", "").upper()
        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not found"}, status=status.HTTP_404_NOT_FOUND)
        item, created = Watchlist.objects.get_or_create(user=request.user, ticker=ticker)
        if not created:
            return Response({"detail": "Already in watchlist"}, status=status.HTTP_409_CONFLICT)
        return Response(WatchlistSerializer(item).data, status=status.HTTP_201_CREATED)


class TickerMoodView(APIView):
    def get(self, request, symbol):
        try:
            ticker = Ticker.objects.get(symbol=symbol.upper())
        except Ticker.DoesNotExist:
            return Response({"detail": f"{symbol} not found"}, status=status.HTTP_404_NOT_FOUND)
        snaps = MarketMoodSnapshot.objects.filter(ticker=ticker)[:24]
        return Response([
            {
                "dominant_mood": s.dominant_mood,
                "confidence": s.confidence,
                "embedding": s.embedding,
                "window_start": s.window_start.isoformat(),
                "window_end": s.window_end.isoformat(),
                "created_at": s.created_at.isoformat(),
            }
            for s in snaps
        ])


class WatchlistDeleteView(APIView):
    def delete(self, request, symbol):
        deleted, _ = Watchlist.objects.filter(
            user=request.user, ticker__symbol=symbol.upper()
        ).delete()
        if deleted == 0:
            return Response({"detail": "Not in watchlist"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

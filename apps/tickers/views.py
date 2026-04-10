from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Ticker, Watchlist
from .serializers import TickerSerializer, WatchlistSerializer


class TickerListCreateView(generics.ListCreateAPIView):
    queryset = Ticker.objects.all().order_by("symbol")
    serializer_class = TickerSerializer


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


class WatchlistDeleteView(APIView):
    def delete(self, request, symbol):
        deleted, _ = Watchlist.objects.filter(
            user=request.user, ticker__symbol=symbol.upper()
        ).delete()
        if deleted == 0:
            return Response({"detail": "Not in watchlist"}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

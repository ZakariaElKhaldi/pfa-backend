from rest_framework import generics
from .models import Ticker
from .serializers import TickerSerializer


class TickerListCreateView(generics.ListCreateAPIView):
    queryset = Ticker.objects.all().order_by("symbol")
    serializer_class = TickerSerializer


class TickerDetailView(generics.RetrieveDestroyAPIView):
    queryset = Ticker.objects.all()
    serializer_class = TickerSerializer
    lookup_field = "symbol"

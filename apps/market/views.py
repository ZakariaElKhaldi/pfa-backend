from rest_framework import generics
from .models import PriceSnapshot
from .serializers import PriceSnapshotSerializer


class TickerPriceListView(generics.ListAPIView):
    serializer_class = PriceSnapshotSerializer

    def get_queryset(self):
        return PriceSnapshot.objects.filter(
            ticker__symbol=self.kwargs["symbol"]
        ).order_by("-timestamp")[:100]

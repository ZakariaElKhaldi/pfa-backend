from rest_framework import generics
from apps.tickers.models import Ticker
from .models import SocialPost
from .serializers import SocialPostSerializer


class TickerPostListView(generics.ListAPIView):
    serializer_class = SocialPostSerializer

    def get_queryset(self):
        symbol = self.kwargs["symbol"]
        return SocialPost.objects.filter(
            ticker__symbol=symbol
        ).order_by("-posted_at")

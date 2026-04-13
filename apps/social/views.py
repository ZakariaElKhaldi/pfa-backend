from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SocialPost
from .serializers import SocialPostSerializer


class TickerPostListView(generics.ListAPIView):
    serializer_class = SocialPostSerializer

    def get_queryset(self):
        symbol = self.kwargs["symbol"]
        return SocialPost.objects.filter(ticker__symbol=symbol).order_by("-posted_at")


class SocialFeedView(generics.ListAPIView):
    serializer_class = SocialPostSerializer
    pagination_class = None

    def get_queryset(self):
        qs = SocialPost.objects.order_by("-posted_at")
        symbol = self.request.query_params.get("symbol")
        if symbol:
            qs = qs.filter(ticker__symbol=symbol.upper())
        return qs[:100]


class TrendingView(APIView):
    def get(self, request):
        since = timezone.now() - timedelta(days=30)
        trending = (
            SocialPost.objects
            .filter(posted_at__gte=since)
            .values("ticker__symbol")
            .annotate(mention_count=Count("id"))
            .order_by("-mention_count")[:10]
        )
        return Response([
            {"symbol": t["ticker__symbol"], "mention_count": t["mention_count"]}
            for t in trending
        ])


class TickerSentimentView(APIView):
    def get(self, request, symbol):
        posts = SocialPost.objects.filter(ticker__symbol=symbol.upper())
        total = posts.count()
        if total == 0:
            return Response({"detail": "No social data."}, status=status.HTTP_404_NOT_FOUND)
        counts = {
            item["sentiment_label"]: item["count"]
            for item in posts.values("sentiment_label").annotate(count=Count("id"))
        }
        bullish = counts.get("bullish", 0)
        bearish = counts.get("bearish", 0)
        neutral = counts.get("neutral", 0)
        return Response({
            "total": total,
            "bullish": bullish,
            "bearish": bearish,
            "neutral": neutral,
            "bullish_pct": round(bullish / total * 100, 1),
            "bearish_pct": round(bearish / total * 100, 1),
            "neutral_pct": round(neutral / total * 100, 1),
        })

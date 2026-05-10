from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .fetchers.google_news import is_relevant_google_post
from .models import SocialPost
from .serializers import SocialPostSerializer

FEED_LIMIT = 100
GLOBAL_CANDIDATE_LIMIT = 5000
GLOBAL_MAX_PER_SOURCE = 40
GLOBAL_MAX_PER_TICKER = 15


class TickerPostListView(generics.ListAPIView):
    serializer_class = SocialPostSerializer

    def get_queryset(self):
        symbol = self.kwargs["symbol"]
        return SocialPost.objects.filter(ticker__symbol=symbol).order_by("-fetched_at", "-posted_at")


class SocialFeedView(generics.ListAPIView):
    serializer_class = SocialPostSerializer
    pagination_class = None

    def get_queryset(self):
        qs = SocialPost.objects.select_related("ticker").order_by("-posted_at", "-fetched_at")
        symbol = self.request.query_params.get("symbol")
        if symbol:
            qs = qs.filter(ticker__symbol=symbol.upper())
        source = self.request.query_params.get("source")
        if source:
            qs = qs.filter(source=source)
        sentiment = self.request.query_params.get("sentiment")
        if sentiment:
            qs = qs.filter(sentiment_label=sentiment)

        if symbol or source or sentiment:
            return self._limited_quality_feed(qs)

        return self._diversified_global_feed(qs)

    def _limited_quality_feed(self, qs):
        selected = []
        for post in qs[:GLOBAL_CANDIDATE_LIMIT]:
            if self._is_quality_feed_post(post):
                selected.append(post)
            if len(selected) >= FEED_LIMIT:
                break
        return selected

    def _diversified_global_feed(self, qs):
        selected = []
        source_counts = {}
        ticker_counts = {}

        for post in qs[:GLOBAL_CANDIDATE_LIMIT]:
            if not self._is_quality_feed_post(post):
                continue
            source_count = source_counts.get(post.source, 0)
            ticker_count = ticker_counts.get(post.ticker_id, 0)
            if source_count < GLOBAL_MAX_PER_SOURCE and ticker_count < GLOBAL_MAX_PER_TICKER:
                selected.append(post)
                source_counts[post.source] = source_count + 1
                ticker_counts[post.ticker_id] = ticker_count + 1

            if len(selected) >= FEED_LIMIT:
                return selected

        return selected

    def _is_quality_feed_post(self, post):
        if post.source != SocialPost.SOURCE_NEWS_GOOGLE:
            return True
        return is_relevant_google_post(
            post.ticker.symbol,
            post.ticker.name,
            post.title,
            post.cleaned_text or post.content,
        )


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

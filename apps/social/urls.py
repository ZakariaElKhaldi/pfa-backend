from django.urls import path

from .views import SocialFeedView, TickerPostListView, TickerSentimentView, TrendingView

urlpatterns = [
    path("tickers/<str:symbol>/posts/", TickerPostListView.as_view(), name="ticker-posts"),
    path("social/feed/", SocialFeedView.as_view(), name="social-feed"),
    path("social/trending/", TrendingView.as_view(), name="social-trending"),
    path("tickers/<str:symbol>/social/sentiment/", TickerSentimentView.as_view(), name="ticker-social-sentiment"),
]

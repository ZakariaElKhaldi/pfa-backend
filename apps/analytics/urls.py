from django.urls import path

from .views import CorrelationView, SentimentLeaderboardView, TopMoversView

urlpatterns = [
    path("top-movers/", TopMoversView.as_view(), name="analytics-top-movers"),
    path("sentiment-leaderboard/", SentimentLeaderboardView.as_view(), name="analytics-sentiment-leaderboard"),
    path("correlation/", CorrelationView.as_view(), name="analytics-correlation"),
]

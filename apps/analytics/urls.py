from django.urls import path

from .views import SentimentLeaderboardView, TopMoversView

urlpatterns = [
    path("top-movers/", TopMoversView.as_view(), name="analytics-top-movers"),
    path("sentiment-leaderboard/", SentimentLeaderboardView.as_view(), name="analytics-sentiment-leaderboard"),
]

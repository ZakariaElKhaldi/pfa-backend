from django.urls import path

from .views import (
    CorrelationView,
    SectorRollupView,
    SentimentLeaderboardView,
    TopMoversView,
)

urlpatterns = [
    path("top-movers/", TopMoversView.as_view(), name="analytics-top-movers"),
    path("sentiment-leaderboard/", SentimentLeaderboardView.as_view(), name="analytics-sentiment-leaderboard"),
    path("correlation/", CorrelationView.as_view(), name="analytics-correlation"),
    path("sector-rollup/", SectorRollupView.as_view(), name="analytics-sector-rollup"),
]

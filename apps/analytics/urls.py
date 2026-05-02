from django.urls import path

from .views import (
    BacktestRunDetailView,
    BacktestRunListCreateView,
    CorrelationView,
    SectorRollupView,
    SentimentLeaderboardView,
    SignalHeatmapView,
    TopMoversView,
)

urlpatterns = [
    path("top-movers/", TopMoversView.as_view(), name="analytics-top-movers"),
    path("sentiment-leaderboard/", SentimentLeaderboardView.as_view(), name="analytics-sentiment-leaderboard"),
    path("correlation/", CorrelationView.as_view(), name="analytics-correlation"),
    path("sector-rollup/", SectorRollupView.as_view(), name="analytics-sector-rollup"),
    path("signal-heatmap/", SignalHeatmapView.as_view(), name="analytics-signal-heatmap"),
    path("backtest/", BacktestRunListCreateView.as_view(), name="analytics-backtest-list"),
    path("backtest/<int:pk>/", BacktestRunDetailView.as_view(), name="analytics-backtest-detail"),
]

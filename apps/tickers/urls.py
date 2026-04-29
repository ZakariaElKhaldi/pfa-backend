from django.urls import path

from .views import (
    TickerDetailView,
    TickerListCreateView,
    TickerMoodView,
    WatchlistDeleteView,
    WatchlistListCreateView,
)

urlpatterns = [
    path("tickers/", TickerListCreateView.as_view(), name="ticker-list"),
    path("tickers/<str:symbol>/mood/", TickerMoodView.as_view(), name="ticker-mood"),
    path("tickers/<str:symbol>/", TickerDetailView.as_view(), name="ticker-detail"),
    path("watchlist/", WatchlistListCreateView.as_view(), name="watchlist-list"),
    path("watchlist/<str:symbol>/", WatchlistDeleteView.as_view(), name="watchlist-delete"),
]

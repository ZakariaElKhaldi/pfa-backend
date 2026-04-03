from django.urls import path

from .views import (
    AlertListView,
    AlertResolveView,
    TickerSignalExplainView,
    TickerSignalHistoryView,
    TickerSignalView,
)

urlpatterns = [
    path("tickers/<str:symbol>/signal/", TickerSignalView.as_view(), name="ticker-signal"),
    path("tickers/<str:symbol>/signal/history/", TickerSignalHistoryView.as_view(), name="ticker-signal-history"),
    path("tickers/<str:symbol>/signal/explain/", TickerSignalExplainView.as_view(), name="ticker-signal-explain"),
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("alerts/<int:pk>/resolve/", AlertResolveView.as_view(), name="alert-resolve"),
]

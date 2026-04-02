from django.urls import path
from .views import TickerSignalView, AlertListView, AlertResolveView

urlpatterns = [
    path("tickers/<str:symbol>/signal/", TickerSignalView.as_view(), name="ticker-signal"),
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("alerts/<int:pk>/resolve/", AlertResolveView.as_view(), name="alert-resolve"),
]

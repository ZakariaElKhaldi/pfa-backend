from django.urls import path

from .views import TickerDetailView, TickerListCreateView

urlpatterns = [
    path("tickers/", TickerListCreateView.as_view(), name="ticker-list"),
    path("tickers/<str:symbol>/", TickerDetailView.as_view(), name="ticker-detail"),
]

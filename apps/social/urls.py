from django.urls import path

from .views import TickerPostListView

urlpatterns = [
    path("tickers/<str:symbol>/posts/", TickerPostListView.as_view(), name="ticker-posts"),
]

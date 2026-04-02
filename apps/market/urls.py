from django.urls import path
from .views import TickerPriceListView

urlpatterns = [
    path("tickers/<str:symbol>/prices/", TickerPriceListView.as_view(), name="ticker-prices"),
]

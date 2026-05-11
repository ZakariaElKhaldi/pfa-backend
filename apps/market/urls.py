from django.urls import path

from .views import MarketClockView, TickerIndicatorsView, TickerPriceListView, TickerQuoteView

urlpatterns = [
    path("market/clock/", MarketClockView.as_view(), name="market-clock"),
    path("tickers/<str:symbol>/prices/", TickerPriceListView.as_view(), name="ticker-prices"),
    path("tickers/<str:symbol>/indicators/", TickerIndicatorsView.as_view(), name="ticker-indicators"),
    path("tickers/<str:symbol>/quote/", TickerQuoteView.as_view(), name="ticker-quote"),
]

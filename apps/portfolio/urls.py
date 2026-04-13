from django.urls import path

from .views import BuyView, PortfolioSummaryView, PortfolioView, SellView, TradeListView

urlpatterns = [
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path("portfolio/buy/", BuyView.as_view(), name="portfolio-buy"),
    path("portfolio/sell/", SellView.as_view(), name="portfolio-sell"),
    path("portfolio/summary/", PortfolioSummaryView.as_view(), name="portfolio-summary"),
    path("portfolio/trades/", TradeListView.as_view(), name="portfolio-trades"),
]

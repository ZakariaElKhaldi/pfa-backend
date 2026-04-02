from django.urls import path
from .views import PortfolioView, BuyView, SellView

urlpatterns = [
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path("portfolio/buy/", BuyView.as_view(), name="portfolio-buy"),
    path("portfolio/sell/", SellView.as_view(), name="portfolio-sell"),
]

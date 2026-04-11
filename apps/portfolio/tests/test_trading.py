import pytest
from decimal import Decimal
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.tickers.models import Ticker
from apps.market.models import PriceSnapshot
from apps.portfolio.models import Portfolio, Position, Trade

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="trader", email="trader@example.com", password="pass123"
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def setup(user, db):
    ticker = Ticker.objects.create(symbol="AAPL", name="Apple Inc.")
    Portfolio.objects.create(user=user, cash=Decimal("100000.00"))
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("150.00"), timestamp=timezone.now()
    )
    return ticker


@pytest.mark.django_db
class TestTradingFlow:
    def test_buy_then_sell(self, auth_client, setup, user):
        # Buy
        resp = auth_client.post("/api/portfolio/buy/", {"symbol": "AAPL", "quantity": 10})
        assert resp.status_code == 200
        assert Decimal(resp.data["cash"]) == Decimal("98500.00")

        # Sell
        resp = auth_client.post("/api/portfolio/sell/", {"symbol": "AAPL", "quantity": 5})
        assert resp.status_code == 200

        portfolio = Portfolio.objects.get(user=user)
        assert portfolio.cash == Decimal("99250.00")
        assert Position.objects.get(portfolio=portfolio).quantity == 5

    def test_insufficient_funds(self, auth_client, setup):
        resp = auth_client.post("/api/portfolio/buy/", {"symbol": "AAPL", "quantity": 1000})
        assert resp.status_code == 400
        assert "Insufficient" in resp.data["detail"]

    def test_sell_more_than_owned(self, auth_client, setup):
        auth_client.post("/api/portfolio/buy/", {"symbol": "AAPL", "quantity": 5})
        resp = auth_client.post("/api/portfolio/sell/", {"symbol": "AAPL", "quantity": 10})
        assert resp.status_code == 400

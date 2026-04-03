from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.market.models import PriceSnapshot
from apps.portfolio.models import Portfolio, Position
from apps.tickers.models import Ticker


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def setup(db):
    ticker = Ticker.objects.create(symbol="AAPL")
    PriceSnapshot.objects.create(ticker=ticker, price="150.00", volume=0, timestamp=timezone.now())
    portfolio = Portfolio.objects.create(name="Test", cash=Decimal("10000.00"))
    return {"ticker": ticker, "portfolio": portfolio}


@pytest.mark.django_db
def test_get_portfolio(client, setup):
    response = client.get("/portfolio/")
    assert response.status_code == 200
    data = response.json()
    assert data["cash"] == "10000.00"
    assert data["positions"] == []


@pytest.mark.django_db
def test_buy_stock(client, setup):
    response = client.post("/portfolio/buy/", {"symbol": "AAPL", "quantity": 10})
    assert response.status_code == 200
    portfolio = Portfolio.objects.first()
    assert portfolio.cash == Decimal("10000.00") - Decimal("150.00") * 10
    position = Position.objects.get(portfolio=portfolio, ticker__symbol="AAPL")
    assert position.quantity == 10


@pytest.mark.django_db
def test_buy_insufficient_funds(client, setup):
    response = client.post("/portfolio/buy/", {"symbol": "AAPL", "quantity": 100})
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()


@pytest.mark.django_db
def test_sell_stock(client, setup):
    # Buy first
    client.post("/portfolio/buy/", {"symbol": "AAPL", "quantity": 5})
    response = client.post("/portfolio/sell/", {"symbol": "AAPL", "quantity": 3})
    assert response.status_code == 200
    position = Position.objects.get(portfolio=Portfolio.objects.first(), ticker__symbol="AAPL")
    assert position.quantity == 2


@pytest.mark.django_db
def test_sell_more_than_owned(client, setup):
    client.post("/portfolio/buy/", {"symbol": "AAPL", "quantity": 2})
    response = client.post("/portfolio/sell/", {"symbol": "AAPL", "quantity": 5})
    assert response.status_code == 400

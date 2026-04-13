import pytest
from decimal import Decimal
from django.utils import timezone
from apps.portfolio.models import Portfolio, Position, Trade
from apps.tickers.models import Ticker
from apps.market.models import PriceSnapshot


@pytest.mark.django_db
def test_summary_returns_correct_shape(auth_client, seeded_portfolio):
    resp = auth_client.get("/api/portfolio/summary/")
    assert resp.status_code == 200
    data = resp.json()
    for key in ("cash", "total_positions_value", "total_value", "total_pnl", "total_pnl_pct", "position_count"):
        assert key in data


@pytest.mark.django_db
def test_summary_cash_only_no_positions(auth_client, seeded_portfolio):
    resp = auth_client.get("/api/portfolio/summary/")
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(data["cash"]) == Decimal("100000.00")
    assert Decimal(data["total_positions_value"]) == Decimal("0")
    assert data["position_count"] == 0


@pytest.mark.django_db
def test_summary_with_position_and_price(auth_client, user, seeded_portfolio, ticker):
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("150.00"), timestamp=timezone.now()
    )
    position = Position.objects.create(
        portfolio=seeded_portfolio, ticker=ticker, quantity=10, avg_price=Decimal("100.00")
    )
    resp = auth_client.get("/api/portfolio/summary/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["position_count"] == 1
    assert Decimal(data["total_positions_value"]) == Decimal("1500.00")


@pytest.mark.django_db
def test_trades_list_empty(auth_client, seeded_portfolio):
    resp = auth_client.get("/api/portfolio/trades/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_trades_list_returns_trades(auth_client, user, seeded_portfolio, ticker):
    Trade.objects.create(
        portfolio=seeded_portfolio, ticker=ticker,
        side="buy", quantity=5, price=Decimal("100.00"),
        executed_at=timezone.now()
    )
    resp = auth_client.get("/api/portfolio/trades/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["side"] == "buy"
    assert data[0]["symbol"] == ticker.symbol

import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


def _seed_prices(ticker, prices):
    """`prices` = list of (hours_ago, price) tuples."""
    now = timezone.now()
    for hours_ago, price in prices:
        PriceSnapshot.objects.create(
            ticker=ticker, price=Decimal(str(price)), volume=1,
            timestamp=now - timedelta(hours=hours_ago),
        )


@pytest.mark.django_db
class TestCorrelationEndpoint:
    URL = "/api/analytics/correlation/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL + "?symbols=AAPL,MSFT").status_code == 403

    def test_requires_at_least_two_symbols(self, analyst_client):
        assert analyst_client.get(self.URL + "?symbols=AAPL").status_code == 400

    def test_too_many_symbols_returns_400(self, analyst_client):
        sym = ",".join(f"T{i}" for i in range(11))
        assert analyst_client.get(f"{self.URL}?symbols={sym}").status_code == 400

    def test_returns_matrix(self, analyst_client):
        a = Ticker.objects.create(symbol="AAPL", name="A")
        b = Ticker.objects.create(symbol="MSFT", name="M")
        _seed_prices(a, [(3, 100), (2, 102), (1, 104)])
        _seed_prices(b, [(3, 50), (2, 51), (1, 52)])
        response = analyst_client.get(self.URL + "?symbols=AAPL,MSFT&window=30d&metric=price")
        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == ["AAPL", "MSFT"]
        assert data["matrix"][0][0] == pytest.approx(1.0)
        assert data["matrix"][1][1] == pytest.approx(1.0)
        assert data["matrix"][0][1] > 0.9

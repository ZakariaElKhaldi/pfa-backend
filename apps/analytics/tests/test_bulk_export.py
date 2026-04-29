import pytest
from decimal import Decimal

from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


@pytest.mark.django_db
class TestBulkExport:
    URL = "/api/export/bulk/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 200

    def test_returns_signals_for_listed_symbols(self, analyst_client):
        a = Ticker.objects.create(symbol="AAPL", name="A")
        b = Ticker.objects.create(symbol="MSFT", name="M")
        for t in (a, b):
            SignalSnapshot.objects.create(
                ticker=t, sentiment=0.0, momentum=0.0, consistency=0.5,
                signal="BUY", post_count=5,
            )
        response = analyst_client.get(self.URL + "?symbols=AAPL,MSFT&include=signals")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        symbols = {row["symbol"] for row in data["signals"]}
        assert symbols == {"AAPL", "MSFT"}

    def test_csv_format(self, analyst_client):
        Ticker.objects.create(symbol="AAPL", name="A")
        response = analyst_client.get(self.URL + "?symbols=AAPL&format=csv&include=signals")
        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")

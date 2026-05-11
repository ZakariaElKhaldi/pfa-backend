import pytest
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


@pytest.mark.django_db
class TestSignalHeatmap:
    URL = "/api/analytics/signal-heatmap/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL + "?symbols=AAPL").status_code == 403

    def test_requires_symbols(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 400

    def test_returns_rows_with_buckets(self, analyst_client):
        t = Ticker.objects.create(symbol="AAPL", name="A")
        now = timezone.now()
        for i in range(3):
            s = SignalSnapshot.objects.create(
                ticker=t, sentiment=0.0, momentum=0.0, consistency=0.5,
                signal="BUY", post_count=10, normalized_index=0.5,
            )
            SignalSnapshot.objects.filter(pk=s.pk).update(
                created_at=now - timedelta(hours=i)
            )
            PriceSnapshot.objects.create(
                ticker=t, price=Decimal("100"), volume=1,
                timestamp=now - timedelta(hours=i),
            )
        response = analyst_client.get(self.URL + "?symbols=AAPL&window=7d")
        data = response.json()
        assert "rows" in data
        assert data["rows"][0]["ticker"] == "AAPL"
        assert isinstance(data["rows"][0]["buckets"], list)
        assert "bucket_start" in data["rows"][0]["buckets"][0]
        assert "signal_avg" in data["rows"][0]["buckets"][0]
        assert "count" in data["rows"][0]["buckets"][0]

import pytest
from datetime import timedelta
from django.utils import timezone

from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


def _signal(t, idx, hours_ago):
    s = SignalSnapshot.objects.create(
        ticker=t, sentiment=idx, momentum=0.0, consistency=0.5,
        signal="BUY", post_count=10, normalized_index=idx,
    )
    SignalSnapshot.objects.filter(pk=s.pk).update(
        created_at=timezone.now() - timedelta(hours=hours_ago)
    )
    s.refresh_from_db()
    return s


@pytest.mark.django_db
class TestSectorRollup:
    URL = "/api/analytics/sector-rollup/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_returns_per_sector_aggregate(self, analyst_client):
        a = Ticker.objects.create(symbol="AAPL", name="Apple", sector="Technology")
        m = Ticker.objects.create(symbol="MSFT", name="MS", sector="Technology")
        x = Ticker.objects.create(symbol="XOM", name="Exxon", sector="Energy")
        _signal(a, 0.7, 1)
        _signal(m, 0.5, 1)
        _signal(x, 0.2, 1)

        results = analyst_client.get(self.URL).json()
        sectors = {r["sector"]: r for r in results}
        assert sectors["Technology"]["ticker_count"] == 2
        assert sectors["Technology"]["avg_signal"] == pytest.approx(0.6, abs=1e-3)
        assert sectors["Energy"]["ticker_count"] == 1

    def test_blank_sector_grouped_as_uncategorised(self, analyst_client):
        t = Ticker.objects.create(symbol="ABC", name="ABC")
        _signal(t, 0.3, 1)
        results = analyst_client.get(self.URL).json()
        sectors = {r["sector"] for r in results}
        assert "Uncategorised" in sectors

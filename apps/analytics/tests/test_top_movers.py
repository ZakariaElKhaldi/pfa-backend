import pytest
from datetime import timedelta
from django.utils import timezone

from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def two_tickers(db):
    a = Ticker.objects.create(symbol="AAPL", name="Apple")
    b = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    return a, b


def _signal(t, sig, idx, hours_ago):
    s = SignalSnapshot.objects.create(
        ticker=t,
        sentiment=0.0, momentum=0.0, consistency=0.5,
        signal=sig, post_count=10, normalized_index=idx,
    )
    SignalSnapshot.objects.filter(pk=s.pk).update(
        created_at=timezone.now() - timedelta(hours=hours_ago)
    )
    s.refresh_from_db()
    return s


@pytest.mark.django_db
class TestTopMoversEndpoint:
    URL = "/api/analytics/top-movers/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 200

    def test_returns_movers_sorted_by_delta(self, analyst_client, two_tickers):
        a, b = two_tickers
        _signal(a, "HOLD", 0.1, hours_ago=20)
        _signal(a, "BUY", 0.9, hours_ago=1)
        _signal(b, "HOLD", 0.5, hours_ago=20)
        _signal(b, "HOLD", 0.4, hours_ago=1)

        response = analyst_client.get(self.URL + "?window=24h&limit=10")
        assert response.status_code == 200
        results = response.json()
        assert len(results) == 2
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["delta"] == pytest.approx(0.8, abs=1e-3)

    def test_invalid_window_returns_400(self, analyst_client):
        assert analyst_client.get(self.URL + "?window=abc").status_code == 400

    def test_empty_returns_empty_list(self, analyst_client):
        assert analyst_client.get(self.URL).json() == []

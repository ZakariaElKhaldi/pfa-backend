import pytest
from datetime import timedelta
from django.utils import timezone

from apps.intelligence.models import MarketMoodSnapshot


@pytest.mark.django_db
class TestMoodSnapshotList:
    URL = "/api/intelligence/mood/"

    def _seed(self, ticker):
        now = timezone.now()
        return MarketMoodSnapshot.objects.create(
            ticker=ticker, embedding=[0.1, 0.2],
            dominant_mood="bullish", confidence=0.8,
            window_start=now - timedelta(hours=1), window_end=now,
        )

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 200

    def test_returns_snapshot_list(self, analyst_client, ticker):
        self._seed(ticker)
        response = analyst_client.get(self.URL)
        assert response.status_code == 200
        data = response.json()
        results = data["results"] if isinstance(data, dict) else data
        assert any(s["dominant_mood"] == "bullish" for s in results)

    def test_filter_by_ticker(self, analyst_client, ticker):
        from apps.tickers.models import Ticker
        other = Ticker.objects.create(symbol="MSFT", name="Microsoft")
        self._seed(ticker)
        self._seed(other)
        response = analyst_client.get(f"{self.URL}?ticker=AAPL")
        assert response.status_code == 200
        data = response.json()
        results = data["results"] if isinstance(data, dict) else data
        assert all(s["ticker_symbol"] == "AAPL" for s in results)

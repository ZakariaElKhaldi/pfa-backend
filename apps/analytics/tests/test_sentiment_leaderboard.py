import pytest
from datetime import timedelta
from django.utils import timezone

from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


def _signal(t, bullish_ratio, posts, hours_ago):
    s = SignalSnapshot.objects.create(
        ticker=t, sentiment=0.0, momentum=0.0, consistency=0.5,
        signal="BUY", post_count=posts, bullish_ratio=bullish_ratio,
    )
    SignalSnapshot.objects.filter(pk=s.pk).update(
        created_at=timezone.now() - timedelta(hours=hours_ago)
    )
    s.refresh_from_db()
    return s


@pytest.mark.django_db
class TestSentimentLeaderboard:
    URL = "/api/analytics/sentiment-leaderboard/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_returns_tickers_sorted_by_bullish_ratio(self, analyst_client):
        a = Ticker.objects.create(symbol="AAPL", name="Apple")
        m = Ticker.objects.create(symbol="MSFT", name="Microsoft")
        _signal(a, 0.9, 50, hours_ago=1)
        _signal(m, 0.4, 30, hours_ago=1)

        results = analyst_client.get(self.URL + "?window=24h").json()
        assert results[0]["ticker"] == "AAPL"
        assert results[0]["bullish_ratio"] == pytest.approx(0.9)

    def test_invalid_window_400(self, analyst_client):
        assert analyst_client.get(self.URL + "?window=zzz").status_code == 400

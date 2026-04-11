import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from unittest.mock import patch

from apps.tickers.models import Ticker
from apps.social.models import SocialPost
from apps.market.models import PriceSnapshot
from apps.signals.engine import compute_signal
from apps.signals.alerts import check_and_create_alert
from apps.signals.models import SignalSnapshot, AlertFlag, DecisionLog


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


@pytest.fixture
def seeded_posts(ticker):
    """Create scored posts to generate a signal."""
    now = timezone.now()
    posts = []
    for i in range(10):
        posts.append(SocialPost.objects.create(
            ticker=ticker,
            source="reddit",
            external_id=f"post_{i}",
            content=f"AAPL is great! Post {i}",
            cleaned_text=f"AAPL is great! Post {i}",
            sentiment_score=0.8,
            sentiment_label="positive",
            fetched_at=now - timedelta(minutes=5),
            posted_at=now - timedelta(minutes=10),
        ))
    return posts


@pytest.fixture
def seeded_prices(ticker):
    now = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("100.00"),
        timestamp=now - timedelta(minutes=25),
    )
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("105.00"),
        timestamp=now - timedelta(minutes=1),
    )


@pytest.mark.django_db
class TestSignalPipelineIntegration:
    @patch("apps.events.bus.publish")
    def test_compute_signal_produces_result(self, mock_publish, ticker, seeded_posts, seeded_prices):
        result = compute_signal("AAPL")
        assert result is not None
        assert result["signal"] in ("BUY", "SELL", "HOLD")
        assert result["post_count"] == 10
        assert "_decision_data" in result

    @patch("apps.events.bus.publish")
    def test_signal_to_snapshot_to_decision_log(self, mock_publish, ticker, seeded_posts, seeded_prices):
        result = compute_signal("AAPL")
        snapshot = SignalSnapshot.objects.create(
            ticker=result["ticker"], sentiment=result["sentiment"],
            momentum=result["momentum"], consistency=result["consistency"],
            signal=result["signal"], post_count=result["post_count"],
        )
        decision_data = result.get("_decision_data", {})
        DecisionLog.objects.create(
            signal_snapshot=snapshot, ticker=ticker,
            input_summary=decision_data.get("input_summary", {}),
            scoring_detail=decision_data.get("scoring_detail", {}),
            engine_output=decision_data.get("engine_output", {}),
        )
        assert DecisionLog.objects.filter(ticker=ticker).count() == 1

    @patch("apps.events.bus.publish")
    def test_alert_creation(self, mock_publish, ticker):
        signal_data = {
            "sentiment": 0.9, "momentum": -0.5, "consistency": 0.2, "post_count": 10
        }
        alert = check_and_create_alert(ticker, signal_data)
        assert alert is not None
        assert alert.type in (AlertFlag.TYPE_EXTREME, AlertFlag.TYPE_DIVERGENCE)

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.signals.engine import compute_signal
from apps.signals.models import SignalSnapshot
from apps.social.models import SocialPost
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


def make_posts(ticker, count, score):
    now = timezone.now()
    for i in range(count):
        SocialPost.objects.create(
            ticker=ticker,
            source=SocialPost.SOURCE_REDDIT,
            external_id=f"test_{i}",
            content="test",
            cleaned_text="test",
            sentiment_score=score,
            sentiment_label=SocialPost.LABEL_BULLISH if score > 0 else SocialPost.LABEL_BEARISH,
            posted_at=now - timedelta(minutes=i),
            fetched_at=now - timedelta(minutes=i),
        )


def make_prices(ticker, start_price, end_price):
    now = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal(str(start_price)),
        volume=0,
        timestamp=now - timedelta(minutes=25),
    )
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal(str(end_price)),
        volume=0,
        timestamp=now,
    )


@pytest.mark.django_db
def test_buy_signal_when_sentiment_high_and_consistent(ticker):
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)  # 7% gain → momentum ≈ 0.7
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_BUY
    assert result["sentiment"] > 0.5
    assert result["consistency"] > 0.5


@pytest.mark.django_db
def test_sell_signal_when_sentiment_low_and_consistent(ticker):
    make_posts(ticker, count=10, score=-0.6)
    make_prices(ticker, start_price=100, end_price=94)  # -6% → momentum ≈ -0.6
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_SELL


@pytest.mark.django_db
def test_hold_signal_when_inconsistent(ticker):
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=93)  # price going down while sentiment up
    result = compute_signal("AAPL")
    assert result is not None
    assert result["signal"] == SignalSnapshot.SIGNAL_HOLD


@pytest.mark.django_db
def test_returns_none_when_no_posts(ticker):
    make_prices(ticker, start_price=100, end_price=105)
    result = compute_signal("AAPL")
    assert result is None


@pytest.mark.django_db
def test_returns_none_for_unknown_ticker():
    result = compute_signal("UNKNOWN")
    assert result is None


@pytest.mark.django_db
def test_post_count_in_result(ticker):
    make_posts(ticker, count=7, score=0.3)
    make_prices(ticker, start_price=100, end_price=100)
    result = compute_signal("AAPL")
    assert result["post_count"] == 7


# --- Phase 2: Aggregation metrics in engine ---


@pytest.mark.django_db
def test_compute_signal_returns_aggregation_metrics(ticker):
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)
    result = compute_signal("AAPL")
    assert "bullish_ratio" in result
    assert "normalized_index" in result
    assert "time_decay_score" in result
    assert "source_weighted_score" in result
    assert "positive_count" in result
    assert "negative_count" in result
    assert "neutral_count" in result


@pytest.mark.django_db
def test_compute_signal_uses_time_decay_for_sentiment(ticker):
    """The primary sentiment should come from time_decay_score, not simple avg."""
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)
    result = compute_signal("AAPL")
    # time_decay_score should be present and close to the post scores
    assert result["time_decay_score"] is not None
    assert abs(result["time_decay_score"] - 0.7) < 0.2


@pytest.mark.django_db
def test_compute_signal_counts_labels(ticker):
    """All posts with score > 0 are bullish, so positive_count should match."""
    make_posts(ticker, count=5, score=0.6)
    make_prices(ticker, start_price=100, end_price=100)
    result = compute_signal("AAPL")
    assert result["positive_count"] == 5
    assert result["negative_count"] == 0

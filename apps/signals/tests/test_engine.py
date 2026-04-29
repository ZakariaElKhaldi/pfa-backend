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


# --- Fade-the-hype guardrail (Long 2024) ---


def build_baseline_posts(ticker, per_window_count: int, windows: int):
    """Create synthetic post history across past 30-min windows with slight variance."""
    now = timezone.now()
    for w in range(1, windows + 1):
        # Alternate ±2 around mean to produce non-zero std
        count = per_window_count + (2 if w % 2 == 0 else -2)
        window_time = now - timedelta(minutes=30 * w + 5)
        for i in range(count):
            post = SocialPost.objects.create(
                ticker=ticker,
                source=SocialPost.SOURCE_REDDIT,
                external_id=f"baseline_w{w}_i{i}",
                content="baseline",
                cleaned_text="baseline",
                sentiment_score=0.0,
                sentiment_label=SocialPost.LABEL_NEUTRAL,
                posted_at=window_time,
                fetched_at=window_time,
            )
            # auto_now_add overrides fetched_at on create — force backdate
            SocialPost.objects.filter(pk=post.pk).update(fetched_at=window_time)


@pytest.mark.django_db
def test_hype_spike_dampens_buy_to_hold(ticker):
    """High baseline + 10x current volume + bullish sentiment → fade to HOLD (Long 2024)."""
    build_baseline_posts(ticker, per_window_count=10, windows=30)
    make_posts(ticker, count=100, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)
    result = compute_signal("AAPL")
    assert result is not None
    assert result["hype_dampened"] is True
    assert result["mention_rate_z"] > 2.0
    assert result["signal"] == SignalSnapshot.SIGNAL_HOLD


@pytest.mark.django_db
def test_no_hype_dampening_when_volume_normal(ticker):
    """Normal volume → guardrail inactive, signal follows sentiment."""
    build_baseline_posts(ticker, per_window_count=10, windows=30)
    make_posts(ticker, count=10, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)
    result = compute_signal("AAPL")
    assert result is not None
    assert result["hype_dampened"] is False
    assert result["signal"] == SignalSnapshot.SIGNAL_BUY


@pytest.mark.django_db
def test_decision_log_records_hype_fields(ticker):
    """scoring_detail must record raw vs dampened sentiment + z-score."""
    build_baseline_posts(ticker, per_window_count=10, windows=30)
    make_posts(ticker, count=100, score=0.7)
    make_prices(ticker, start_price=100, end_price=107)
    result = compute_signal("AAPL")
    detail = result["_decision_data"]["scoring_detail"]
    assert "raw_sentiment" in detail
    assert "mention_rate_z" in detail
    assert "hype_dampened" in detail
    assert detail["hype_dampened"] is True
    assert detail["raw_sentiment"] > detail["sentiment"]

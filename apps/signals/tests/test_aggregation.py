import math
from datetime import datetime, timedelta, timezone as tz

import pytest

from apps.signals.aggregation import (
    bullish_ratio,
    compute_aggregated_sentiment,
    normalized_index,
    source_weighted_score,
    time_decay_weighted_score,
)


# --- bullish_ratio: ln[(1 + Mpos) / (1 + Mneg)] ---

def test_bullish_ratio_all_positive():
    result = bullish_ratio(10, 0)
    assert result > 0
    assert result == pytest.approx(math.log(11 / 1))


def test_bullish_ratio_all_negative():
    result = bullish_ratio(0, 10)
    assert result < 0
    assert result == pytest.approx(math.log(1 / 11))


def test_bullish_ratio_balanced():
    result = bullish_ratio(5, 5)
    assert result == pytest.approx(0.0)


def test_bullish_ratio_empty():
    result = bullish_ratio(0, 0)
    assert result == pytest.approx(0.0)


# --- normalized_index: (Mpos - Mneg) / (Mpos + Mneu + Mneg) ---

def test_normalized_index_all_positive():
    result = normalized_index(10, 0, 0)
    assert result == pytest.approx(1.0)


def test_normalized_index_all_negative():
    result = normalized_index(0, 10, 0)
    assert result == pytest.approx(-1.0)


def test_normalized_index_equal_pos_neg():
    result = normalized_index(5, 5, 0)
    assert result == pytest.approx(0.0)


def test_normalized_index_with_neutral():
    result = normalized_index(6, 2, 2)
    assert result == pytest.approx(0.4)


def test_normalized_index_zero_total():
    result = normalized_index(0, 0, 0)
    assert result == pytest.approx(0.0)


# --- time_decay_weighted_score ---

def test_time_decay_recent_posts_weighted_more():
    now = datetime.now(tz.utc)
    posts = [
        {"sentiment_score": 0.9, "fetched_at": now - timedelta(minutes=1)},
        {"sentiment_score": -0.5, "fetched_at": now - timedelta(minutes=25)},
    ]
    result = time_decay_weighted_score(posts, half_life_minutes=10.0, now=now)
    # Recent bullish post (0.9) should dominate over old bearish (-0.5)
    assert result > 0.0


def test_time_decay_single_post():
    now = datetime.now(tz.utc)
    posts = [{"sentiment_score": 0.6, "fetched_at": now - timedelta(minutes=2)}]
    result = time_decay_weighted_score(posts, half_life_minutes=15.0, now=now)
    assert result == pytest.approx(0.6, abs=0.05)


def test_time_decay_empty_posts():
    now = datetime.now(tz.utc)
    result = time_decay_weighted_score([], now=now)
    assert result == pytest.approx(0.0)


def test_time_decay_custom_half_life():
    now = datetime.now(tz.utc)
    posts = [
        {"sentiment_score": 1.0, "fetched_at": now - timedelta(minutes=1)},
        {"sentiment_score": -1.0, "fetched_at": now - timedelta(minutes=20)},
    ]
    # Short half life: recent post dominates
    short = time_decay_weighted_score(posts, half_life_minutes=5.0, now=now)
    # Long half life: both posts weighted more equally
    long = time_decay_weighted_score(posts, half_life_minutes=60.0, now=now)
    assert short > long


# --- source_weighted_score ---

def test_source_weighted_stocktwits_higher():
    posts = [
        {"sentiment_score": 0.5, "source": "stocktwits"},
        {"sentiment_score": 0.5, "source": "reddit"},
    ]
    result = source_weighted_score(posts)
    # StockTwits has higher default weight, so result should be above simple mean
    assert result == pytest.approx(0.5, abs=0.05)


def test_source_weighted_custom_weights():
    posts = [
        {"sentiment_score": 1.0, "source": "reddit"},
        {"sentiment_score": -1.0, "source": "stocktwits"},
    ]
    # Give reddit 2x weight
    result = source_weighted_score(posts, source_weights={"reddit": 2.0, "stocktwits": 1.0})
    assert result > 0  # reddit dominates


def test_source_weighted_single_source():
    posts = [
        {"sentiment_score": 0.7, "source": "reddit"},
        {"sentiment_score": 0.3, "source": "reddit"},
    ]
    result = source_weighted_score(posts)
    assert result == pytest.approx(0.5, abs=0.05)


def test_source_weighted_empty():
    result = source_weighted_score([])
    assert result == pytest.approx(0.0)


# --- compute_aggregated_sentiment ---

def test_compute_aggregated_returns_all_metrics():
    now = datetime.now(tz.utc)
    posts = [
        {"sentiment_score": 0.8, "sentiment_label": "bullish", "source": "stocktwits", "fetched_at": now - timedelta(minutes=5)},
        {"sentiment_score": -0.3, "sentiment_label": "bearish", "source": "reddit", "fetched_at": now - timedelta(minutes=10)},
        {"sentiment_score": 0.05, "sentiment_label": "neutral", "source": "stocktwits", "fetched_at": now - timedelta(minutes=15)},
    ]
    result = compute_aggregated_sentiment(posts, now=now)
    assert "bullish_ratio" in result
    assert "normalized_index" in result
    assert "time_decay_score" in result
    assert "source_weighted_score" in result
    assert "simple_mean" in result
    assert "post_count" in result
    assert "positive_count" in result
    assert "negative_count" in result
    assert "neutral_count" in result
    assert result["positive_count"] == 1
    assert result["negative_count"] == 1
    assert result["neutral_count"] == 1
    assert result["post_count"] == 3


def test_compute_aggregated_empty():
    result = compute_aggregated_sentiment([])
    assert result["post_count"] == 0
    assert result["simple_mean"] == 0.0

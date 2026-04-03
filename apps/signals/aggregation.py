"""
Sentiment aggregation methods based on research papers:
- Paper 4 (PeerJ CS 2023): normalized_index = (Mpos - Mneg) / (Mpos + Mneu + Mneg)
- Paper 5 (Nature 2024): bullish_ratio = ln[(1 + Mpos) / (1 + Mneg)], time-decay, volume weighting
- Paper 2 (MDPI JRFM 2025): source-weighted aggregation (StockTwits > Reddit)

All functions are pure (no ORM dependency) and operate on lists of dicts.
"""

import math
from datetime import datetime, timezone as tz

DEFAULT_SOURCE_WEIGHTS = {
    "stocktwits": 1.2,
    "reddit": 1.0,
    "news_alpaca": 1.5,
    "news_yahoo": 1.5,
    "news_google": 1.3,
}


def bullish_ratio(pos_count: int, neg_count: int) -> float:
    """ln[(1 + Mpos) / (1 + Mneg)] -- Paper 5."""
    return math.log((1 + pos_count) / (1 + neg_count))


def normalized_index(pos_count: int, neg_count: int, neu_count: int) -> float:
    """(Mpos - Mneg) / (Mpos + Mneu + Mneg) -- Paper 4."""
    total = pos_count + neg_count + neu_count
    if total == 0:
        return 0.0
    return (pos_count - neg_count) / total


def time_decay_weighted_score(
    posts: list[dict],
    half_life_minutes: float = 15.0,
    now: datetime | None = None,
) -> float:
    """Exponential time-decay weighted average of sentiment scores -- Paper 5."""
    if not posts:
        return 0.0
    if now is None:
        now = datetime.now(tz.utc)

    decay_lambda = math.log(2) / half_life_minutes
    weighted_sum = 0.0
    weight_total = 0.0

    for post in posts:
        age_minutes = (now - post["fetched_at"]).total_seconds() / 60.0
        weight = math.exp(-decay_lambda * max(age_minutes, 0.0))
        weighted_sum += post["sentiment_score"] * weight
        weight_total += weight

    if weight_total == 0:
        return 0.0
    return weighted_sum / weight_total


def source_weighted_score(
    posts: list[dict],
    source_weights: dict | None = None,
) -> float:
    """Source-weighted average -- Paper 2: StockTwits > Reddit in predictive power."""
    if not posts:
        return 0.0
    weights = source_weights or DEFAULT_SOURCE_WEIGHTS

    weighted_sum = 0.0
    weight_total = 0.0
    for post in posts:
        w = weights.get(post["source"], 1.0)
        weighted_sum += post["sentiment_score"] * w
        weight_total += w

    if weight_total == 0:
        return 0.0
    return weighted_sum / weight_total


def compute_aggregated_sentiment(
    posts: list[dict],
    now: datetime | None = None,
) -> dict:
    """
    Compute all aggregation metrics from a list of post dicts.
    Each post dict must have: sentiment_score, sentiment_label, source, fetched_at.
    """
    if not posts:
        return {
            "bullish_ratio": 0.0,
            "normalized_index": 0.0,
            "time_decay_score": 0.0,
            "source_weighted_score": 0.0,
            "simple_mean": 0.0,
            "post_count": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
        }

    pos_count = sum(1 for p in posts if p["sentiment_label"] == "bullish")
    neg_count = sum(1 for p in posts if p["sentiment_label"] == "bearish")
    neu_count = sum(1 for p in posts if p["sentiment_label"] == "neutral")

    scores = [p["sentiment_score"] for p in posts]
    simple_mean = sum(scores) / len(scores)

    return {
        "bullish_ratio": bullish_ratio(pos_count, neg_count),
        "normalized_index": normalized_index(pos_count, neg_count, neu_count),
        "time_decay_score": time_decay_weighted_score(posts, now=now),
        "source_weighted_score": source_weighted_score(posts),
        "simple_mean": simple_mean,
        "post_count": len(posts),
        "positive_count": pos_count,
        "negative_count": neg_count,
        "neutral_count": neu_count,
    }

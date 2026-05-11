import logging
from datetime import timedelta

from django.utils import timezone

from apps.signals.aggregation import compute_aggregated_sentiment
from apps.signals.hype import apply_hype_dampener, compute_mention_rate_z
from apps.signals.models import SignalSnapshot

logger = logging.getLogger(__name__)

BUY_SENTIMENT_THRESHOLD = 0.5
SELL_SENTIMENT_THRESHOLD = -0.3
CONSISTENCY_THRESHOLD = 0.5
HYPE_BASELINE_DAYS = 30
HYPE_WINDOW_MINUTES = 30
HYPE_Z_THRESHOLD = 2.0
HYPE_LAMBDA = 0.5


def _price_sources_for_momentum(price_model) -> tuple[str, ...]:
    """
    Prefer live Alpaca prices. In local/dev data sets, seed prices are the only
    available momentum source, so allow them as a fallback only when needed.
    """
    return price_model.LIVE_SOURCES


def _compute_baseline_counts(ticker, now, window_minutes: int, lookback_days: int) -> list[int]:
    """Return per-window post counts over last `lookback_days`, excluding current window."""
    from apps.social.models import SocialPost

    window_seconds = window_minutes * 60
    baseline_start = now - timedelta(days=lookback_days)
    current_window_start = now - timedelta(minutes=window_minutes)

    posts = list(
        SocialPost.objects.filter(
            ticker=ticker,
            fetched_at__gte=baseline_start,
            fetched_at__lt=current_window_start,
        ).values_list("fetched_at", flat=True)
    )
    if not posts:
        return []
    counts: dict[int, int] = {}
    for ts in posts:
        bucket = int(ts.timestamp() // window_seconds)
        counts[bucket] = counts.get(bucket, 0) + 1
    return list(counts.values())


def compute_signal(ticker_symbol: str) -> dict | None:
    """
    Returns dict with signal data including advanced aggregation metrics,
    or None if insufficient data.
    """
    from apps.market.models import PriceSnapshot
    from apps.social.models import SocialPost
    from apps.tickers.models import Ticker

    try:
        ticker = Ticker.objects.get(symbol=ticker_symbol)
    except Ticker.DoesNotExist:
        return None

    now = timezone.now()
    cutoff = now - timedelta(minutes=30)

    # Fetch scored posts from last 30 minutes
    posts_qs = SocialPost.objects.filter(
        ticker=ticker,
        fetched_at__gte=cutoff,
        sentiment_score__isnull=False,
    )
    post_count = posts_qs.count()
    if post_count == 0:
        total_posts = SocialPost.objects.filter(ticker=ticker).count()
        unscored_posts = SocialPost.objects.filter(
            ticker=ticker,
            sentiment_score__isnull=True,
        ).count()
        recent_posts = SocialPost.objects.filter(
            ticker=ticker,
            fetched_at__gte=cutoff,
        ).count()
        logger.info(
            "No signal for %s: total_posts=%d unscored=%d in_window=%d scored_in_window=0 cutoff=%s",
            ticker_symbol,
            total_posts,
            unscored_posts,
            recent_posts,
            cutoff.isoformat(),
        )
        return None

    # Build post dicts for aggregation
    post_dicts = list(
        posts_qs.values("sentiment_score", "sentiment_label", "source", "fetched_at")
    )

    # Compute aggregated sentiment (Papers 4 & 5)
    agg = compute_aggregated_sentiment(post_dicts, now=now)

    # Use time-decay weighted score as primary sentiment (Paper 5)
    raw_sentiment = agg["time_decay_score"]

    # Fade-the-hype guardrail (Long 2024): dampen sentiment if mention rate spikes
    baseline_counts = _compute_baseline_counts(
        ticker, now, HYPE_WINDOW_MINUTES, HYPE_BASELINE_DAYS
    )
    mention_rate_z = compute_mention_rate_z(post_count, baseline_counts)
    sentiment, hype_dampened = apply_hype_dampener(
        raw_sentiment, mention_rate_z, z_threshold=HYPE_Z_THRESHOLD, lambda_=HYPE_LAMBDA
    )

    # Momentum: % price change over last 30 minutes, normalized to [-1, 1]
    price_sources = _price_sources_for_momentum(PriceSnapshot)
    prices = PriceSnapshot.objects.filter(
        ticker=ticker,
        timestamp__gte=cutoff,
        source__in=price_sources,
    ).order_by("timestamp")

    if prices.count() < 2:
        seed_prices = PriceSnapshot.objects.filter(
            ticker=ticker,
            timestamp__gte=cutoff,
            source=PriceSnapshot.SOURCE_SEED,
        ).order_by("timestamp")
        if seed_prices.count() >= 2:
            prices = seed_prices
            price_sources = (PriceSnapshot.SOURCE_SEED,)
            logger.info(
                "Using seed price fallback for %s momentum: no live price pair in the last 30 minutes",
                ticker_symbol,
            )

    if prices.count() >= 2:
        oldest_price = float(prices.first().price)
        newest_price = float(prices.last().price)
        if oldest_price > 0:
            raw_momentum = (newest_price - oldest_price) / oldest_price
            momentum = max(-1.0, min(1.0, raw_momentum * 10))
        else:
            momentum = 0.0
    else:
        momentum = 0.0
        logger.info(
            "Momentum unavailable for %s: price_count=%d sources=%s cutoff=%s",
            ticker_symbol,
            prices.count(),
            price_sources,
            cutoff.isoformat(),
        )

    consistency = 1.0 - abs(sentiment - momentum) / 2.0

    if sentiment > BUY_SENTIMENT_THRESHOLD and consistency > CONSISTENCY_THRESHOLD:
        signal = SignalSnapshot.SIGNAL_BUY
    elif sentiment < SELL_SENTIMENT_THRESHOLD and consistency > CONSISTENCY_THRESHOLD:
        signal = SignalSnapshot.SIGNAL_SELL
    else:
        signal = SignalSnapshot.SIGNAL_HOLD

    result = {
        "ticker": ticker,
        "sentiment": sentiment,
        "momentum": momentum,
        "consistency": consistency,
        "signal": signal,
        "post_count": post_count,
        # Aggregation metrics
        "bullish_ratio": agg["bullish_ratio"],
        "normalized_index": agg["normalized_index"],
        "time_decay_score": agg["time_decay_score"],
        "source_weighted_score": agg["source_weighted_score"],
        "positive_count": agg["positive_count"],
        "negative_count": agg["negative_count"],
        "neutral_count": agg["neutral_count"],
        # Fade-the-hype guardrail (Long 2024)
        "raw_sentiment": raw_sentiment,
        "mention_rate_z": mention_rate_z,
        "hype_dampened": hype_dampened,
    }

    # Decision logging
    decision_data = {
        "input_summary": {
            "post_count": post_count,
            "cutoff": cutoff.isoformat(),
            "sources": sorted({p["source"] for p in post_dicts}),
            "price_sources": list(price_sources),
        },
        "scoring_detail": {
            "aggregation": agg,
            "sentiment": sentiment,
            "raw_sentiment": raw_sentiment,
            "mention_rate_z": mention_rate_z,
            "hype_dampened": hype_dampened,
            "momentum": momentum,
            "consistency": consistency,
        },
        "engine_output": {
            "signal": signal,
            "thresholds": {
                "buy_sentiment": BUY_SENTIMENT_THRESHOLD,
                "sell_sentiment": SELL_SENTIMENT_THRESHOLD,
                "consistency": CONSISTENCY_THRESHOLD,
            },
        },
    }
    result["_decision_data"] = decision_data

    from apps.events.bus import publish
    from apps.events.types import SIGNAL_GENERATED

    publish(SIGNAL_GENERATED, {
        "ticker": ticker_symbol,
        "signal": signal,
        "sentiment": sentiment,
        "momentum": momentum,
        "consistency": consistency,
        "post_count": post_count,
    })

    return result

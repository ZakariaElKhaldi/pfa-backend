import logging
from datetime import timedelta

from django.utils import timezone

from apps.signals.aggregation import compute_aggregated_sentiment
from apps.signals.models import SignalSnapshot

logger = logging.getLogger(__name__)


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

    cutoff = timezone.now() - timedelta(minutes=30)

    # Fetch scored posts from last 30 minutes
    posts_qs = SocialPost.objects.filter(
        ticker=ticker,
        fetched_at__gte=cutoff,
        sentiment_score__isnull=False,
    )
    post_count = posts_qs.count()
    if post_count == 0:
        return None

    # Build post dicts for aggregation
    post_dicts = list(
        posts_qs.values("sentiment_score", "sentiment_label", "source", "fetched_at")
    )

    # Compute aggregated sentiment (Papers 4 & 5)
    agg = compute_aggregated_sentiment(post_dicts, now=timezone.now())

    # Use time-decay weighted score as primary sentiment (Paper 5)
    sentiment = agg["time_decay_score"]

    # Momentum: % price change over last 30 minutes, normalized to [-1, 1]
    prices = PriceSnapshot.objects.filter(ticker=ticker, timestamp__gte=cutoff).order_by(
        "timestamp"
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

    consistency = 1.0 - abs(sentiment - momentum) / 2.0

    if sentiment > 0.5 and consistency > 0.5:
        signal = SignalSnapshot.SIGNAL_BUY
    elif sentiment < -0.3 and consistency > 0.5:
        signal = SignalSnapshot.SIGNAL_SELL
    else:
        signal = SignalSnapshot.SIGNAL_HOLD

    return {
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
    }

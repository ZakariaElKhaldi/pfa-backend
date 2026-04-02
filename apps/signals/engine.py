import logging
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from apps.signals.models import SignalSnapshot

logger = logging.getLogger(__name__)


def compute_signal(ticker_symbol: str) -> dict | None:
    """
    Returns dict with keys: ticker, sentiment, momentum, consistency, signal, post_count
    or None if insufficient data.
    """
    from apps.tickers.models import Ticker
    from apps.social.models import SocialPost
    from apps.market.models import PriceSnapshot

    try:
        ticker = Ticker.objects.get(symbol=ticker_symbol)
    except Ticker.DoesNotExist:
        return None

    cutoff = timezone.now() - timedelta(minutes=30)

    # Sentiment: average score over last 30 minutes
    posts = SocialPost.objects.filter(
        ticker=ticker,
        fetched_at__gte=cutoff,
        sentiment_score__isnull=False,
    )
    post_count = posts.count()
    if post_count == 0:
        return None

    sentiment = posts.aggregate(avg=Avg("sentiment_score"))["avg"]

    # Momentum: % price change over last 30 minutes, normalized to [-1, 1]
    prices = PriceSnapshot.objects.filter(
        ticker=ticker, timestamp__gte=cutoff
    ).order_by("timestamp")

    if prices.count() >= 2:
        oldest_price = float(prices.first().price)
        newest_price = float(prices.last().price)
        if oldest_price > 0:
            raw_momentum = (newest_price - oldest_price) / oldest_price
            # Scale: 10% change → 1.0 (clip at ±1)
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
    }

"""
Feature engineering: combine sentiment + technical features into a single vector.
Based on Papers 1 & 4: 3 sentiment features + 7+ technical features.
"""

import math
from datetime import timedelta

from django.utils import timezone

from apps.market.indicators import (
    bollinger_bands,
    ema,
    historical_volatility,
    macd,
    rsi,
    sma,
)


def build_feature_vector(ticker_symbol: str, window_minutes: int = 30) -> dict | None:
    """
    Build a combined feature vector for the given ticker.
    Returns dict of {feature_name: value} or None if ticker not found.
    """
    from apps.market.models import PriceSnapshot
    from apps.social.models import SocialPost
    from apps.tickers.models import Ticker

    try:
        ticker = Ticker.objects.get(symbol=ticker_symbol)
    except Ticker.DoesNotExist:
        return None

    features = {}

    # --- Technical features ---
    price_qs = PriceSnapshot.objects.filter(ticker=ticker).order_by("timestamp")
    prices_list = list(price_qs.values_list("price", flat=True))
    close_prices = [float(p) for p in prices_list]

    if close_prices:
        features["close"] = close_prices[-1]
        volumes = list(price_qs.values_list("volume", flat=True))
        features["volume"] = volumes[-1] if volumes else None
        features["sma_20"] = sma(close_prices, 20)
        features["ema_12"] = ema(close_prices, 12)
        features["rsi_14"] = rsi(close_prices, 14)

        bb = bollinger_bands(close_prices, 20)
        if bb:
            bandwidth = (bb["upper"] - bb["lower"]) / bb["middle"] if bb["middle"] != 0 else None
            features["bollinger_bandwidth"] = bandwidth
        else:
            features["bollinger_bandwidth"] = None

        macd_result = macd(close_prices)
        features["macd_histogram"] = macd_result["histogram"] if macd_result else None

        features["volatility"] = historical_volatility(close_prices, 20)
    else:
        for key in ["close", "volume", "sma_20", "ema_12", "rsi_14",
                     "bollinger_bandwidth", "macd_histogram", "volatility"]:
            features[key] = None

    # --- Sentiment features ---
    cutoff = timezone.now() - timedelta(minutes=window_minutes)
    posts = SocialPost.objects.filter(
        ticker=ticker,
        fetched_at__gte=cutoff,
        sentiment_score__isnull=False,
    )
    scores = list(posts.values_list("sentiment_score", flat=True))

    if scores:
        mean = sum(scores) / len(scores)
        features["sentiment_mean"] = mean
        if len(scores) > 1:
            variance = sum((s - mean) ** 2 for s in scores) / (len(scores) - 1)
            features["sentiment_std"] = math.sqrt(variance)
        else:
            features["sentiment_std"] = 0.0
        features["sentiment_max"] = max(scores)
        features["sentiment_min"] = min(scores)

        labels = list(posts.values_list("sentiment_label", flat=True))
        pos_count = labels.count("bullish")
        features["positive_ratio"] = pos_count / len(labels)
        features["post_count"] = len(scores)
    else:
        for key in ["sentiment_mean", "sentiment_std", "sentiment_max",
                     "sentiment_min", "positive_ratio", "post_count"]:
            features[key] = None

    return features

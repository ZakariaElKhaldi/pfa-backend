import logging

from apps.sentiment.scorer import SentimentScorer
from apps.social.cleaner import clean_text, is_quality_post
from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher
from apps.social.fetchers.alpaca_news import AlpacaNewsFetcher
from apps.social.fetchers.yahoo_news import YahooNewsFetcher
from apps.social.fetchers.google_news import GoogleNewsFetcher

logger = logging.getLogger(__name__)


def run_pipeline_for_ticker(symbol: str) -> None:
    """
    Full pipeline for one ticker:
      1. Fetch posts (Reddit + StockTwits)
      2. Clean + filter low-quality
      3. Store new posts (deduplicate)
      4. Batch score unscored posts with FinBERT
      5. Compute signal snapshot with advanced aggregation
      6. Generate alerts if triggered
      7. Push enriched update via WebSocket
    """
    from apps.market.utils import push_market_update
    from apps.signals.alerts import check_and_create_alert
    from apps.signals.engine import compute_signal
    from apps.signals.models import DecisionLog, SignalSnapshot
    from apps.social.models import SocialPost
    from apps.tickers.models import Ticker

    try:
        ticker = Ticker.objects.get(symbol=symbol)
    except Ticker.DoesNotExist:
        logger.error("Ticker %s not found", symbol)
        return

    scorer = SentimentScorer()
    fetchers = [
        RedditFetcher(),
        StockTwitsFetcher(),
        AlpacaNewsFetcher(),
        YahooNewsFetcher(),
        GoogleNewsFetcher()
    ]

    # Step 1-3: Fetch, clean, store
    for fetcher in fetchers:
        try:
            raw_posts = fetcher.fetch(symbol)
        except Exception as e:
            logger.error("%s fetch failed for %s: %s", fetcher.__class__.__name__, symbol, e)
            continue

        for post_data in raw_posts:
            cleaned = clean_text(post_data["content"])
            if not is_quality_post(cleaned):
                continue
            SocialPost.objects.get_or_create(
                source=post_data["source"],
                external_id=post_data["external_id"],
                defaults={
                    "ticker": ticker,
                    "title": post_data.get("title"),
                    "url": post_data.get("url"),
                    "content": post_data["content"],
                    "cleaned_text": cleaned,
                    "posted_at": post_data["posted_at"],
                },
            )

    # Step 4: Batch score unscored posts
    unscored = list(SocialPost.objects.filter(ticker=ticker, sentiment_score__isnull=True))
    if unscored:
        texts = [post.cleaned_text or post.content for post in unscored]
        try:
            details = scorer.score_batch(texts)
            for post, detail in zip(unscored, details):
                post.sentiment_score = detail["composite_score"]
                post.sentiment_label = detail["label"]
                post.positive_prob = detail["positive_prob"]
                post.negative_prob = detail["negative_prob"]
                post.neutral_prob = detail["neutral_prob"]
            SocialPost.objects.bulk_update(
                unscored,
                ["sentiment_score", "sentiment_label", "positive_prob", "negative_prob", "neutral_prob"],
            )
        except Exception as e:
            logger.error("Batch scoring failed for %s: %s", symbol, e)

    # Step 5: Compute signal with advanced aggregation
    result = compute_signal(symbol)
    if result is None:
        logger.info("No signal computed for %s (insufficient data)", symbol)
        return

    snapshot = SignalSnapshot.objects.create(
        ticker=result["ticker"],
        sentiment=result["sentiment"],
        momentum=result["momentum"],
        consistency=result["consistency"],
        signal=result["signal"],
        post_count=result["post_count"],
        # Advanced aggregation metrics
        bullish_ratio=result.get("bullish_ratio"),
        normalized_index=result.get("normalized_index"),
        time_decay_score=result.get("time_decay_score"),
        source_weighted_score=result.get("source_weighted_score"),
        positive_count=result.get("positive_count", 0),
        negative_count=result.get("negative_count", 0),
        neutral_count=result.get("neutral_count", 0),
    )

    # Decision logging
    decision_data = result.get("_decision_data", {})
    if decision_data:
        DecisionLog.objects.create(
            signal_snapshot=snapshot,
            ticker=ticker,
            input_summary=decision_data.get("input_summary", {}),
            scoring_detail=decision_data.get("scoring_detail", {}),
            engine_output=decision_data.get("engine_output", {}),
        )

    # Step 6: Alerts
    check_and_create_alert(ticker, result)

    # Step 7: Push enriched WebSocket payload
    push_market_update(
        symbol,
        {
            "type": "signal",
            "signal": snapshot.signal,
            "prediction_method": snapshot.prediction_method,
            "prediction_confidence": snapshot.prediction_confidence,
            "sentiment": {
                "time_decay": snapshot.time_decay_score,
                "bullish_ratio": snapshot.bullish_ratio,
                "normalized_index": snapshot.normalized_index,
                "source_weighted": snapshot.source_weighted_score,
                "simple_mean": snapshot.sentiment,
            },
            "counts": {
                "positive": snapshot.positive_count,
                "negative": snapshot.negative_count,
                "neutral": snapshot.neutral_count,
            },
            "momentum": snapshot.momentum,
            "consistency": snapshot.consistency,
            "post_count": snapshot.post_count,
        },
    )
    logger.info("Pipeline complete for %s: %s", symbol, snapshot.signal)

    from apps.events.bus import publish
    from apps.events.types import PIPELINE_COMPLETED

    publish(PIPELINE_COMPLETED, {
        "ticker": symbol,
        "signal": snapshot.signal,
        "post_count": snapshot.post_count,
    })

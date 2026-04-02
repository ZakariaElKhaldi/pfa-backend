import logging

from apps.social.cleaner import clean_text, is_quality_post
from apps.social.fetchers.reddit import RedditFetcher
from apps.social.fetchers.stocktwits import StockTwitsFetcher
from apps.sentiment.scorer import SentimentScorer

logger = logging.getLogger(__name__)


def run_pipeline_for_ticker(symbol: str) -> None:
    """
    Full pipeline for one ticker:
      1. Fetch posts (Reddit + StockTwits)
      2. Clean + filter low-quality
      3. Store new posts (deduplicate)
      4. Score unscored posts with FinBERT
      5. Compute signal snapshot
      6. Generate alerts if triggered
      7. Push update via WebSocket
    """
    from apps.tickers.models import Ticker
    from apps.social.models import SocialPost
    from apps.signals.engine import compute_signal
    from apps.signals.alerts import check_and_create_alert
    from apps.signals.models import SignalSnapshot
    from apps.market.utils import push_market_update

    try:
        ticker = Ticker.objects.get(symbol=symbol)
    except Ticker.DoesNotExist:
        logger.error("Ticker %s not found", symbol)
        return

    scorer = SentimentScorer()
    fetchers = [RedditFetcher(), StockTwitsFetcher()]

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
                    "content": post_data["content"],
                    "cleaned_text": cleaned,
                    "posted_at": post_data["posted_at"],
                },
            )

    # Step 4: Score unscored posts
    unscored = SocialPost.objects.filter(ticker=ticker, sentiment_score__isnull=True)
    for post in unscored:
        try:
            score, label = scorer.score(post.cleaned_text or post.content)
            post.sentiment_score = score
            post.sentiment_label = label
            post.save(update_fields=["sentiment_score", "sentiment_label"])
        except Exception as e:
            logger.error("Scoring failed for post %s: %s", post.id, e)

    # Step 5: Compute signal
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
    )

    # Step 6: Alerts
    check_and_create_alert(ticker, result)

    # Step 7: Push
    push_market_update(
        symbol,
        {
            "type": "signal",
            "signal": snapshot.signal,
            "sentiment": snapshot.sentiment,
            "momentum": snapshot.momentum,
            "consistency": snapshot.consistency,
            "post_count": snapshot.post_count,
        },
    )
    logger.info("Pipeline complete for %s: %s", symbol, snapshot.signal)

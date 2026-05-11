import logging

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)

PIPELINE_LOCK_KEY = "pipeline.run_pipeline.lock"
PIPELINE_LOCK_TIMEOUT_SECONDS = 10 * 60


@shared_task(name="pipeline.run_pipeline")
def run_pipeline() -> None:
    """Celery task: run fallback ingestion for all tracked tickers."""
    from apps.pipeline.pipeline import run_pipeline_for_ticker
    from apps.tickers.models import Ticker

    if not cache.add(PIPELINE_LOCK_KEY, "1", timeout=PIPELINE_LOCK_TIMEOUT_SECONDS):
        logger.warning("Pipeline already running; skipping overlapping run")
        return

    symbols = list(Ticker.objects.values_list("symbol", flat=True))
    logger.info("Running pipeline for %d tickers: %s", len(symbols), symbols)

    try:
        for symbol in symbols:
            try:
                run_pipeline_for_ticker(symbol)
            except Exception as e:
                logger.error("Pipeline failed for %s: %s", symbol, e)
    finally:
        cache.delete(PIPELINE_LOCK_KEY)

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="pipeline.run_pipeline")
def run_pipeline() -> None:
    """Celery task: run ingestion pipeline for all tracked tickers."""
    from apps.pipeline.pipeline import run_pipeline_for_ticker
    from apps.tickers.models import Ticker

    symbols = list(Ticker.objects.values_list("symbol", flat=True))
    logger.info("Running pipeline for %d tickers: %s", len(symbols), symbols)

    for symbol in symbols:
        try:
            run_pipeline_for_ticker(symbol)
        except Exception as e:
            logger.error("Pipeline failed for %s: %s", symbol, e)

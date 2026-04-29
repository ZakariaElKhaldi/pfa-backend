"""Celery tasks for intelligence app."""

import logging

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone

from apps.intelligence.memory import compute_mood_snapshot
from apps.intelligence.models import RetrainLog

logger = logging.getLogger(__name__)


@shared_task(name="intelligence.compute_mood_snapshots")
def compute_mood_snapshots_all() -> int:
    """Compute market mood snapshot for every watched ticker. Hourly cadence."""
    from apps.tickers.models import Ticker, Watchlist

    symbols = set(
        Watchlist.objects.values_list("ticker__symbol", flat=True).distinct()
    )
    count = 0
    for symbol in symbols:
        try:
            ticker = Ticker.objects.get(symbol=symbol)
        except Ticker.DoesNotExist:
            continue
        try:
            if compute_mood_snapshot(ticker) is not None:
                count += 1
        except Exception as exc:
            logger.exception("Mood snapshot failed for %s: %s", symbol, exc)
    return count


@shared_task
def auto_retrain(ticker_symbol: str) -> None:
    """Run train_signal_model management command for a ticker, update RetrainLog."""
    log = (
        RetrainLog.objects.filter(
            ticker__symbol=ticker_symbol, status="running"
        )
        .order_by("-started_at")
        .first()
    )
    try:
        call_command("train_signal_model", ticker=ticker_symbol)
        if log:
            log.status = "success"
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "completed_at"])
        _reload_model_cache(ticker_symbol)
    except Exception as exc:
        logger.exception("Retrain failed for %s: %s", ticker_symbol, exc)
        if log:
            log.status = "failed"
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "completed_at"])


def _reload_model_cache(ticker_symbol: str) -> None:
    from apps.signals.ml.predictor import SignalPredictor

    predictor = SignalPredictor()
    predictor._model_cache.pop(ticker_symbol, None)

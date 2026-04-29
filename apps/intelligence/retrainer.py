"""Auto-retrain loop (Ruan 2025 concept-drift retraining)."""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.intelligence.models import RetrainLog

logger = logging.getLogger(__name__)

MIN_ACCURACY_RECORDS = 50
ROLLING_WINDOW = 50
ACCURACY_FLOOR = 0.6
COOLDOWN_HOURS = 24


def check_and_maybe_retrain(ticker_symbol: str) -> RetrainLog | None:
    """Trigger retrain if rolling accuracy below floor and cooldown passed."""
    from apps.signals.models import SignalAccuracy
    from apps.tickers.models import Ticker

    try:
        ticker = Ticker.objects.get(symbol=ticker_symbol)
    except Ticker.DoesNotExist:
        return None

    accuracy_qs = SignalAccuracy.objects.filter(
        signal_snapshot__ticker=ticker,
        accuracy_24h__isnull=False,
    ).order_by("-evaluated_at")[:ROLLING_WINDOW]
    records = list(accuracy_qs)
    if len(records) < MIN_ACCURACY_RECORDS:
        return None

    wins = sum(1 for r in records if r.accuracy_24h)
    win_rate = wins / len(records)
    if win_rate >= ACCURACY_FLOOR:
        return None

    cooldown_cutoff = timezone.now() - timedelta(hours=COOLDOWN_HOURS)
    recent = RetrainLog.objects.filter(
        ticker=ticker, started_at__gte=cooldown_cutoff
    ).exists()
    if recent:
        return None

    log = RetrainLog.objects.create(
        ticker=ticker,
        trigger_reason="accuracy_below_threshold",
        old_accuracy=win_rate,
        status="running",
    )
    _enqueue_retrain(ticker_symbol)
    logger.info("Retrain triggered for %s (win_rate=%.3f)", ticker_symbol, win_rate)
    return log


def _enqueue_retrain(ticker_symbol: str) -> None:
    """Enqueue Celery retrain task (patched in tests)."""
    from apps.intelligence.tasks import auto_retrain

    auto_retrain.delay(ticker_symbol)

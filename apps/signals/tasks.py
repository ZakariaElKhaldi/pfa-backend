import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.signals.models import SignalAccuracy, SignalSnapshot

logger = logging.getLogger(__name__)


def _get_price_near(ticker, target_time, tolerance_minutes=10):
    """Find the closest price snapshot to target_time within tolerance."""
    window_start = target_time - timedelta(minutes=tolerance_minutes)
    window_end = target_time + timedelta(minutes=tolerance_minutes)
    snap = (
        PriceSnapshot.objects.filter(
            ticker=ticker, timestamp__gte=window_start, timestamp__lte=window_end
        )
        .order_by("timestamp")
        .first()
    )
    return snap.price if snap else None


def _direction(price_before, price_after):
    diff = float(price_after - price_before)
    if diff > 0:
        return "UP"
    elif diff < 0:
        return "DOWN"
    return "FLAT"


def _signal_matches_direction(signal, direction):
    if signal == "BUY" and direction == "UP":
        return True
    if signal == "SELL" and direction == "DOWN":
        return True
    if signal == "HOLD" and direction == "FLAT":
        return True
    return False


@shared_task(name="signals.evaluate_accuracy")
def evaluate_signal_accuracy():
    """Evaluate signals older than 1h that haven't been evaluated yet."""
    cutoff = timezone.now() - timedelta(hours=1)
    snapshots = SignalSnapshot.objects.filter(
        created_at__lte=cutoff, accuracy__isnull=True
    ).select_related("ticker")

    for snapshot in snapshots:
        price_at_signal = _get_price_near(snapshot.ticker, snapshot.created_at)
        if price_at_signal is None:
            continue

        price_1h = _get_price_near(
            snapshot.ticker, snapshot.created_at + timedelta(hours=1)
        )
        price_24h = _get_price_near(
            snapshot.ticker, snapshot.created_at + timedelta(hours=24)
        )

        actual_1h = _direction(price_at_signal, price_1h) if price_1h else None
        accuracy_1h = _signal_matches_direction(snapshot.signal, actual_1h) if actual_1h else None

        actual_24h = _direction(price_at_signal, price_24h) if price_24h else None
        accuracy_24h = _signal_matches_direction(snapshot.signal, actual_24h) if actual_24h else None

        actual_direction = actual_1h or actual_24h or "FLAT"

        SignalAccuracy.objects.create(
            signal_snapshot=snapshot,
            predicted=snapshot.signal,
            actual_direction=actual_direction,
            price_at_signal=price_at_signal,
            price_after_1h=price_1h,
            price_after_24h=price_24h,
            accuracy_1h=accuracy_1h,
            accuracy_24h=accuracy_24h,
        )
        logger.info("Evaluated %s: %s → %s", snapshot.ticker.symbol, snapshot.signal, actual_direction)

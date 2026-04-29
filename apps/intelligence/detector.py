"""Volume-anomaly manipulation detector (La Morgia 2023 adapted — minute-level proxy)."""

import math
from datetime import timedelta

PUMP_SCORE_THRESHOLD = 3.0
BASELINE_DAYS = 30
MIN_BASELINE_SAMPLES = 5
MIN_POST_COUNT = 50


def detect_pump_pattern(ticker, signal_data: dict):
    """Flag pump-and-dump pattern: volume spike + sentiment swing + low consistency."""
    from django.utils import timezone

    from apps.intelligence.models import ManipulationFlag
    from apps.market.models import PriceSnapshot

    now = timezone.now()
    current = (
        PriceSnapshot.objects.filter(ticker=ticker, timestamp__lte=now)
        .order_by("-timestamp")
        .first()
    )
    if current is None:
        return None

    baseline_qs = (
        PriceSnapshot.objects.filter(
            ticker=ticker,
            timestamp__gte=now - timedelta(days=BASELINE_DAYS),
            timestamp__lt=current.timestamp,
        )
        .exclude(pk=current.pk)
        .values_list("volume", flat=True)
    )
    baseline = list(baseline_qs)
    if len(baseline) < MIN_BASELINE_SAMPLES:
        return None

    z = compute_volume_z(current_volume=float(current.volume), baseline_volumes=baseline)
    sentiment_delta = float(signal_data.get("sentiment_delta_1h", 0.0))
    consistency = float(signal_data.get("consistency", 0.0))
    post_count = int(signal_data.get("post_count", 0))

    score = compute_pump_score(z, sentiment_delta, consistency)
    if score <= PUMP_SCORE_THRESHOLD or post_count < MIN_POST_COUNT:
        return None

    baseline_mean = sum(baseline) / len(baseline)
    confidence = max(0.0, min(1.0, score / 6.0))
    return ManipulationFlag.objects.create(
        ticker=ticker,
        pattern_type="pump_dump",
        confidence=confidence,
        evidence={
            "z_score": z,
            "sentiment_delta": sentiment_delta,
            "post_count": post_count,
            "comparable_30d_mean": baseline_mean,
            "pump_score": score,
            "consistency": consistency,
        },
    )


def compute_pump_score(
    volume_z: float,
    sentiment_delta: float,
    consistency: float,
    alpha: float = 1.0,
    beta: float = 1.0,
    gamma: float = 1.0,
) -> float:
    return alpha * volume_z + beta * abs(sentiment_delta) - gamma * consistency


def compute_volume_z(current_volume: float, baseline_volumes: list[float]) -> float:
    if not baseline_volumes:
        return 0.0
    n = len(baseline_volumes)
    mean = sum(baseline_volumes) / n
    variance = sum((v - mean) ** 2 for v in baseline_volumes) / n
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (current_volume - mean) / std

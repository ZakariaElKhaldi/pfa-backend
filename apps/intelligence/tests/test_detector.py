"""Volume-anomaly manipulation detector (La Morgia 2023 adapted)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.intelligence.detector import (
    compute_pump_score,
    compute_volume_z,
    detect_pump_pattern,
)
from apps.intelligence.models import ManipulationFlag
from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


def test_compute_volume_z_empty_baseline_returns_zero():
    """No history → 0, safe no-op."""
    assert compute_volume_z(current_volume=10_000, baseline_volumes=[]) == 0.0


def test_compute_volume_z_zero_std_returns_zero():
    """Constant baseline → z=0, safe no-op."""
    assert compute_volume_z(current_volume=50, baseline_volumes=[10, 10, 10]) == 0.0


def test_compute_volume_z_spike_returns_positive_z():
    """Volume 10x baseline → high positive z."""
    z = compute_volume_z(current_volume=100_000, baseline_volumes=[9_000, 10_000, 11_000, 10_000])
    assert z > 5.0


def test_compute_volume_z_normal_volume_returns_low_z():
    """Current near baseline mean → z ≈ 0."""
    z = compute_volume_z(current_volume=10_000, baseline_volumes=[9_000, 10_000, 11_000, 10_000])
    assert abs(z) < 1.0


def test_compute_pump_score_formula():
    """PumpScore = α·z + β·|Δsent| − γ·consistency (La Morgia 2023 adapted)."""
    score = compute_pump_score(
        volume_z=4.0, sentiment_delta=0.8, consistency=0.2,
        alpha=1.0, beta=1.0, gamma=1.0,
    )
    assert score == pytest.approx(4.0 + 0.8 - 0.2)


def test_compute_pump_score_defaults_alpha_1_beta_1_gamma_1():
    score = compute_pump_score(volume_z=3.0, sentiment_delta=0.5, consistency=0.5)
    assert score == pytest.approx(3.0)


def test_compute_pump_score_penalises_high_consistency():
    """High consistency (organic market move) → lower pump score."""
    noisy = compute_pump_score(volume_z=3.0, sentiment_delta=0.5, consistency=0.2)
    organic = compute_pump_score(volume_z=3.0, sentiment_delta=0.5, consistency=0.9)
    assert noisy > organic


# --- Orchestrator: detect_pump_pattern ---


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


def seed_baseline_volumes(ticker, count: int, volume: int):
    """Create historical PriceSnapshots across past minutes (stable volume)."""
    now = timezone.now()
    for i in range(count):
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal("100.00"),
            volume=volume + (100 if i % 2 == 0 else -100),
            timestamp=now - timedelta(minutes=30 + i),
        )


def seed_current_volume(ticker, volume: int):
    """Current-minute price snapshot."""
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("100.00"),
        volume=volume,
        timestamp=timezone.now(),
    )


@pytest.mark.django_db
def test_detect_pump_pattern_none_when_below_threshold(ticker):
    """Normal volume + low sentiment delta → no flag."""
    seed_baseline_volumes(ticker, count=100, volume=10_000)
    seed_current_volume(ticker, volume=10_500)
    signal_data = {
        "sentiment": 0.1,
        "sentiment_delta_1h": 0.05,
        "consistency": 0.8,
        "post_count": 10,
    }
    result = detect_pump_pattern(ticker, signal_data)
    assert result is None
    assert ManipulationFlag.objects.count() == 0


@pytest.mark.django_db
def test_detect_pump_pattern_creates_flag_on_volume_spike(ticker):
    """10x volume + high sentiment swing + low consistency → ManipulationFlag."""
    seed_baseline_volumes(ticker, count=100, volume=10_000)
    seed_current_volume(ticker, volume=200_000)
    signal_data = {
        "sentiment": 0.8,
        "sentiment_delta_1h": 1.5,
        "consistency": 0.2,
        "post_count": 200,
    }
    result = detect_pump_pattern(ticker, signal_data)
    assert result is not None
    assert isinstance(result, ManipulationFlag)
    assert result.pattern_type == "pump_dump"
    assert result.confidence > 0.7
    assert "z_score" in result.evidence
    assert "sentiment_delta" in result.evidence
    assert "post_count" in result.evidence
    assert "comparable_30d_mean" in result.evidence


@pytest.mark.django_db
def test_detect_pump_pattern_no_flag_without_baseline(ticker):
    """No baseline → can't compute z, no flag (safe no-op)."""
    seed_current_volume(ticker, volume=500_000)
    signal_data = {
        "sentiment": 0.9,
        "sentiment_delta_1h": 1.5,
        "consistency": 0.1,
        "post_count": 200,
    }
    result = detect_pump_pattern(ticker, signal_data)
    assert result is None

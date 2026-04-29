"""Auto-retrain loop tests (Ruan 2025 concept-drift retraining)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.intelligence.models import RetrainLog
from apps.intelligence.retrainer import check_and_maybe_retrain
from apps.signals.models import SignalAccuracy, SignalSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


def make_accuracy_records(ticker, count: int, win_rate: float):
    """Create `count` SignalAccuracy rows with given 24h win rate."""
    wins = int(count * win_rate)
    for i in range(count):
        snap = SignalSnapshot.objects.create(
            ticker=ticker,
            sentiment=0.5,
            momentum=0.0,
            consistency=0.5,
            signal="HOLD",
            post_count=5,
        )
        SignalAccuracy.objects.create(
            signal_snapshot=snap,
            predicted="HOLD",
            actual_direction="FLAT",
            price_at_signal=100,
            accuracy_24h=(i < wins),
        )


@pytest.mark.django_db
def test_skips_when_record_count_below_threshold(ticker):
    """< 50 accuracy records → no retrain (Ruan 2025)."""
    make_accuracy_records(ticker, count=30, win_rate=0.3)
    result = check_and_maybe_retrain("AAPL")
    assert result is None
    assert RetrainLog.objects.count() == 0


@pytest.mark.django_db
def test_skips_when_accuracy_above_threshold(ticker):
    """50 records but 70% win rate → no retrain (above 60% floor)."""
    make_accuracy_records(ticker, count=50, win_rate=0.7)
    result = check_and_maybe_retrain("AAPL")
    assert result is None
    assert RetrainLog.objects.count() == 0


@pytest.mark.django_db
def test_triggers_retrain_when_accuracy_below_threshold(ticker, monkeypatch):
    """50 records, 30% win rate, no prior retrain → creates RetrainLog."""
    called = {"count": 0}

    def fake_enqueue(symbol):
        called["count"] += 1

    monkeypatch.setattr("apps.intelligence.retrainer._enqueue_retrain", fake_enqueue)
    make_accuracy_records(ticker, count=50, win_rate=0.3)
    result = check_and_maybe_retrain("AAPL")
    assert result is not None
    assert isinstance(result, RetrainLog)
    assert result.ticker == ticker
    assert result.status == "running"
    assert result.old_accuracy == pytest.approx(0.3, abs=0.05)
    assert result.trigger_reason == "accuracy_below_threshold"
    assert called["count"] == 1


@pytest.mark.django_db
def test_skips_when_recent_retrain_within_cooldown(ticker, monkeypatch):
    """Prior retrain within 24h → skip, even if accuracy bad (safeguard)."""
    called = {"count": 0}
    monkeypatch.setattr(
        "apps.intelligence.retrainer._enqueue_retrain",
        lambda s: called.__setitem__("count", called["count"] + 1),
    )
    RetrainLog.objects.create(
        ticker=ticker,
        trigger_reason="accuracy_below_threshold",
        old_accuracy=0.3,
        status="success",
    )
    make_accuracy_records(ticker, count=50, win_rate=0.3)
    result = check_and_maybe_retrain("AAPL")
    assert result is None
    assert RetrainLog.objects.count() == 1
    assert called["count"] == 0


@pytest.mark.django_db
def test_evaluate_signal_accuracy_invokes_retrainer_check(ticker, monkeypatch):
    """Accuracy evaluation task must call check_and_maybe_retrain per ticker."""
    from decimal import Decimal

    from apps.market.models import PriceSnapshot
    from apps.signals.tasks import evaluate_signal_accuracy

    called = []

    def fake_check(symbol):
        called.append(symbol)
        return None

    monkeypatch.setattr("apps.signals.tasks.check_and_maybe_retrain", fake_check)

    now = timezone.now()
    snap = SignalSnapshot.objects.create(
        ticker=ticker, sentiment=0.5, momentum=0.0, consistency=0.5,
        signal="HOLD", post_count=5,
    )
    SignalSnapshot.objects.filter(pk=snap.pk).update(created_at=now - timedelta(hours=2))
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("100.00"), timestamp=now - timedelta(hours=2),
    )
    PriceSnapshot.objects.create(
        ticker=ticker, price=Decimal("100.00"), timestamp=now - timedelta(minutes=55),
    )
    evaluate_signal_accuracy()
    assert "AAPL" in called


@pytest.mark.django_db
def test_triggers_retrain_when_prior_retrain_older_than_cooldown(ticker, monkeypatch):
    """Prior retrain > 24h ago → cooldown passed, retrain triggers."""
    monkeypatch.setattr("apps.intelligence.retrainer._enqueue_retrain", lambda s: None)
    old_log = RetrainLog.objects.create(
        ticker=ticker,
        trigger_reason="accuracy_below_threshold",
        old_accuracy=0.3,
        status="success",
    )
    # Backdate started_at beyond cooldown
    RetrainLog.objects.filter(pk=old_log.pk).update(
        started_at=timezone.now() - timedelta(hours=25)
    )
    make_accuracy_records(ticker, count=50, win_rate=0.3)
    result = check_and_maybe_retrain("AAPL")
    assert result is not None
    assert RetrainLog.objects.count() == 2

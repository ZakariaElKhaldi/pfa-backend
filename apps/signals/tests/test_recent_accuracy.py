import pytest
from decimal import Decimal
from django.utils import timezone
from apps.signals.models import SignalSnapshot, SignalAccuracy
from apps.tickers.models import Ticker, Watchlist


@pytest.mark.django_db
def test_recent_signals_empty_watchlist(auth_client, user):
    """Returns empty list when user has empty watchlist."""
    resp = auth_client.get("/api/signals/recent/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_recent_signals_from_watchlist(auth_client, user, ticker):
    """Returns signals only for tickers in user's watchlist."""
    Watchlist.objects.create(user=user, ticker=ticker)
    snap = SignalSnapshot.objects.create(
        ticker=ticker,
        signal="BUY",
        sentiment=0.6,
        momentum=0.4,
        consistency=0.8,
        post_count=10,
        bullish_ratio=0.6,
        normalized_index=0.5,
        time_decay_score=0.7,
        source_weighted_score=0.6,
        prediction_method="rule_based",
        prediction_confidence=0.75,
        feature_importances={},
    )
    resp = auth_client.get("/api/signals/recent/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["signal"] == "BUY"


@pytest.mark.django_db
def test_recent_signals_limit(auth_client, user, ticker):
    """Respects limit query param."""
    Watchlist.objects.create(user=user, ticker=ticker)
    for i in range(5):
        SignalSnapshot.objects.create(
            ticker=ticker, signal="HOLD", sentiment=0.5, momentum=0.5,
            consistency=0.5, post_count=1, bullish_ratio=0.5,
            normalized_index=0.5, time_decay_score=0.5,
            source_weighted_score=0.5, prediction_method="rule_based",
            prediction_confidence=0.5, feature_importances={},
        )
    resp = auth_client.get("/api/signals/recent/?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) <= 3


@pytest.mark.django_db
def test_recent_signals_admin_all_returns_platform_signals(admin_client, ticker):
    """Admin dashboard can request platform-wide recent signals."""
    SignalSnapshot.objects.create(
        ticker=ticker, signal="SELL", sentiment=-0.6, momentum=-0.4,
        consistency=0.8, post_count=10, bullish_ratio=0.2,
        normalized_index=-0.5, time_decay_score=-0.7,
        source_weighted_score=-0.6, prediction_method="rule_based",
        prediction_confidence=0.75, feature_importances={},
    )
    resp = admin_client.get("/api/signals/recent/?limit=8&all=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["signal"] == "SELL"


@pytest.mark.django_db
def test_global_accuracy_no_data(auth_client):
    """Returns null overall_pct when no evaluated signals."""
    resp = auth_client.get("/api/signals/accuracy/global/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_pct"] is None
    assert data["total_evaluated"] == 0


@pytest.mark.django_db
def test_global_accuracy_with_data(auth_client, ticker):
    """Computes accuracy from evaluated SignalAccuracy records."""
    snap = SignalSnapshot.objects.create(
        ticker=ticker, signal="BUY", sentiment=0.6, momentum=0.4,
        consistency=0.8, post_count=10, bullish_ratio=0.6,
        normalized_index=0.5, time_decay_score=0.7,
        source_weighted_score=0.6, prediction_method="rule_based",
        prediction_confidence=0.75, feature_importances={},
    )
    SignalAccuracy.objects.create(
        signal_snapshot=snap,
        predicted="BUY",
        actual_direction="UP",
        price_at_signal=Decimal("100.00"),
        price_after_1h=Decimal("101.00"),
        price_after_24h=Decimal("102.00"),
        accuracy_1h=True,
        accuracy_24h=True,
        evaluated_at=timezone.now(),
    )
    resp = auth_client.get("/api/signals/accuracy/global/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_pct"] == 100.0
    assert data["total_evaluated"] == 1
    assert "BUY" in data["by_signal"]

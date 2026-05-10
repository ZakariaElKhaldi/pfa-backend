from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.analytics.views import BreadthForecastView, VolumeForecastView
from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


def _seed_volume(symbol: str = "AAPL", points: int = 12):
    ticker = Ticker.objects.create(symbol=symbol, name=symbol)
    now = timezone.now()
    for i in range(points):
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal("100.00"),
            open_price=Decimal("99.00"),
            high_price=Decimal("101.00"),
            low_price=Decimal("98.00"),
            volume=1_000_000 + i,
            timestamp=now - timedelta(days=i),
        )
    return ticker


@pytest.mark.django_db
def test_volume_forecast_returns_503_when_timesfm_unavailable(monkeypatch, admin_user):
    _seed_volume(points=12)
    from apps.analytics import timesfm_service

    monkeypatch.setattr(timesfm_service, "timesfm", None)
    req = APIRequestFactory().get("/api/analytics/forecast/volume/?ticker=AAPL")
    force_authenticate(req, user=admin_user)
    resp = VolumeForecastView.as_view()(req)
    assert resp.status_code == 503
    assert resp.data["code"] == "TIMESFM_UNAVAILABLE"
    assert resp.data["model_status"] == "TIMESFM_UNAVAILABLE"


@pytest.mark.django_db
def test_volume_forecast_returns_400_for_insufficient_history(admin_user):
    _seed_volume(points=5)
    req = APIRequestFactory().get("/api/analytics/forecast/volume/?ticker=AAPL")
    force_authenticate(req, user=admin_user)
    resp = VolumeForecastView.as_view()(req)
    assert resp.status_code == 400
    assert resp.data["code"] == "INSUFFICIENT_HISTORY"


@pytest.mark.django_db
def test_volume_forecast_returns_200_with_mocked_forecast(monkeypatch, admin_user):
    _seed_volume(points=12)
    from apps.analytics import timesfm_service

    monkeypatch.setattr(timesfm_service, "check_timesfm_ready", lambda: None)
    monkeypatch.setattr(
        timesfm_service,
        "forecast_volume",
        lambda *_args, **_kwargs: [1.0, 2.0, 3.0],
    )
    req = APIRequestFactory().get("/api/analytics/forecast/volume/?ticker=AAPL")
    force_authenticate(req, user=admin_user)
    resp = VolumeForecastView.as_view()(req)
    assert resp.status_code == 200
    assert resp.data["forecast"] == [1.0, 2.0, 3.0]
    assert resp.data["method"] == "timesfm"
    assert resp.data["model_status"] == "ready"


@pytest.mark.django_db
def test_volume_forecast_does_not_cache_error_responses(monkeypatch, admin_user):
    _seed_volume(symbol="TSLA", points=12)
    from apps.analytics import timesfm_service

    req = APIRequestFactory().get("/api/analytics/forecast/volume/?ticker=TSLA")
    force_authenticate(req, user=admin_user)

    monkeypatch.setattr(timesfm_service, "check_timesfm_ready", lambda: None)
    monkeypatch.setattr(
        timesfm_service,
        "forecast_volume",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    resp1 = VolumeForecastView.as_view()(req)
    assert resp1.status_code == 500
    assert resp1.data["code"] == "FORECAST_INFERENCE_FAILED"

    monkeypatch.setattr(
        timesfm_service,
        "forecast_volume",
        lambda *_args, **_kwargs: [10.0, 20.0, 30.0],
    )
    resp2 = VolumeForecastView.as_view()(req)
    assert resp2.status_code == 200
    assert resp2.data["forecast"] == [10.0, 20.0, 30.0]


def _seed_signal_history(points: int = 36):
    ticker = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    now = timezone.now()
    signals = ["BUY", "SELL", "HOLD"]
    for i in range(points):
        created_at = now - (timedelta(hours=i) if i < 24 else timedelta(days=i - 22))
        s = SignalSnapshot.objects.create(
            ticker=ticker,
            sentiment=0.0,
            momentum=0.0,
            consistency=0.5,
            signal=signals[i % len(signals)],
            post_count=10,
        )
        SignalSnapshot.objects.filter(pk=s.pk).update(created_at=created_at)


@pytest.mark.django_db
@pytest.mark.parametrize("window", ["1d", "7d", "30d", "90d"])
def test_breadth_forecast_returns_history_for_supported_windows(monkeypatch, admin_user, window):
    _seed_signal_history()
    from apps.analytics import timesfm_service

    monkeypatch.setattr(timesfm_service, "check_timesfm_ready", lambda: None)
    monkeypatch.setattr(timesfm_service, "forecast_series", lambda *_args, **_kwargs: [1.0, 2.0])
    req = APIRequestFactory().get(f"/api/analytics/forecast/breadth/?window={window}")
    force_authenticate(req, user=admin_user)
    resp = BreadthForecastView.as_view()(req)
    assert resp.status_code == 200
    assert len(resp.data["history"]) >= 2
    assert {"bucket", "buy", "sell", "hold", "net", "cumulative"} <= set(resp.data["history"][0])
    assert resp.data["forecast"] == [1.0, 2.0]
    assert resp.data["method"] == "timesfm"
    assert resp.data["model_status"] == "ready"


@pytest.mark.django_db
def test_breadth_forecast_returns_503_when_timesfm_unavailable(monkeypatch, admin_user):
    _seed_signal_history()
    from apps.analytics import timesfm_service

    monkeypatch.setattr(timesfm_service, "timesfm", None)
    req = APIRequestFactory().get("/api/analytics/forecast/breadth/?window=30d")
    force_authenticate(req, user=admin_user)
    resp = BreadthForecastView.as_view()(req)
    assert resp.status_code == 503
    assert resp.data["code"] == "TIMESFM_UNAVAILABLE"
    assert len(resp.data["history"]) >= 2

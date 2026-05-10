from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.analytics.views import VolumeForecastView
from apps.market.models import PriceSnapshot
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
    monkeypatch.setattr(timesfm_service, "forecast_volume", lambda *_args, **_kwargs: [1.0, 2.0, 3.0])
    req = APIRequestFactory().get("/api/analytics/forecast/volume/?ticker=AAPL")
    force_authenticate(req, user=admin_user)
    resp = VolumeForecastView.as_view()(req)
    assert resp.status_code == 200
    assert resp.data["forecast"] == [1.0, 2.0, 3.0]

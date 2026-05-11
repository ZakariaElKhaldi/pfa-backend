from unittest.mock import patch

import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser


@pytest.fixture
def mkt_user(db):
    return CustomUser.objects.create_user(
        username="clocktest", email="clocktest@example.com", password="pass"
    )


@pytest.fixture
def mkt_client(mkt_user):
    c = APIClient()
    token = RefreshToken.for_user(mkt_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.mark.django_db
@patch("apps.market.views.config")
@patch("alpaca.trading.client.TradingClient")
def test_market_clock_returns_shape(mock_trading_client, mock_config, mkt_client):
    mock_config.side_effect = lambda key, default="": "x" if key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY") else default

    class _T:
        def __init__(self, value):
            self.value = value

        def isoformat(self):
            return self.value

    clock = type(
        "Clock",
        (),
        {
            "is_open": False,
            "next_open": _T("2026-05-11T09:30:00-04:00"),
            "next_close": _T("2026-05-11T16:00:00-04:00"),
            "timestamp": _T("2026-05-11T04:13:30-04:00"),
        },
    )()
    mock_trading_client.return_value.get_clock.return_value = clock

    resp = mkt_client.get("/api/market/clock/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_open"] is False
    assert "next_open" in body
    assert "next_close" in body
    assert "server_timestamp" in body


@pytest.mark.django_db
@patch("apps.market.views.config")
def test_market_clock_503_without_credentials(mock_config, mkt_client):
    mock_config.return_value = ""
    resp = mkt_client.get("/api/market/clock/")
    assert resp.status_code == 503

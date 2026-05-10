import pytest
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker, Watchlist


def _auth_client_for(user: CustomUser) -> APIClient:
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
def test_user_scope_flag_off_keeps_legacy_behavior():
    user = CustomUser.objects.create_user(
        username="scope_off", email="scope_off@example.com", password="pass123", role="user"
    )
    ticker = Ticker.objects.create(symbol="AAPL", name="Apple")
    Watchlist.objects.create(user=user, ticker=ticker)
    SignalSnapshot.objects.create(
        ticker=ticker,
        sentiment=0.4,
        momentum=0.3,
        consistency=0.8,
        signal="BUY",
        post_count=5,
    )

    client = _auth_client_for(user)
    resp = client.get("/api/signals/recent/?limit=1")
    assert resp.status_code == 200


@pytest.mark.django_db
@override_settings(ENFORCE_USER_SCOPE_PERMISSIONS=True)
def test_user_scope_flag_on_blocks_missing_scope():
    user = CustomUser.objects.create_user(
        username="scope_blocked",
        email="scope_blocked@example.com",
        password="pass123",
        role="user",
        permissions=[],
    )
    client = _auth_client_for(user)
    resp = client.get("/api/signals/recent/?limit=1")
    assert resp.status_code == 403


@pytest.mark.django_db
@override_settings(ENFORCE_USER_SCOPE_PERMISSIONS=True)
def test_user_scope_flag_on_allows_matching_scope():
    user = CustomUser.objects.create_user(
        username="scope_allowed",
        email="scope_allowed@example.com",
        password="pass123",
        role="user",
        permissions=["signals.read"],
    )
    ticker = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    Watchlist.objects.create(user=user, ticker=ticker)
    SignalSnapshot.objects.create(
        ticker=ticker,
        sentiment=0.2,
        momentum=0.1,
        consistency=0.7,
        signal="HOLD",
        post_count=2,
    )

    client = _auth_client_for(user)
    resp = client.get("/api/signals/recent/?limit=1")
    assert resp.status_code == 200

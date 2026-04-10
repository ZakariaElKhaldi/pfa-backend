import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.signals.models import SignalSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


@pytest.mark.django_db
class TestExport:
    def test_export_json(self, auth_client, ticker):
        SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.8, momentum=0.5, consistency=0.7,
            signal="BUY", post_count=10,
        )
        resp = auth_client.get(f"/api/export/{ticker.symbol}/?format=json&include=signals")
        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert len(data["signals"]) == 1

    def test_export_csv(self, auth_client, ticker):
        SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.8, momentum=0.5, consistency=0.7,
            signal="BUY", post_count=10,
        )
        resp = auth_client.get(f"/api/export/{ticker.symbol}/?format=csv&include=signals")
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv"

    def test_unauthenticated_denied(self, ticker):
        client = APIClient()
        resp = client.get(f"/api/export/{ticker.symbol}/")
        assert resp.status_code == 401

    def test_unknown_ticker_returns_404(self, auth_client):
        resp = auth_client.get("/api/export/NOPE/?include=signals")
        assert resp.status_code == 404

    def test_invalid_date_returns_400(self, auth_client, ticker):
        resp = auth_client.get(f"/api/export/{ticker.symbol}/?from=not-a-date")
        assert resp.status_code == 400

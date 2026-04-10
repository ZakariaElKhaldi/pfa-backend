import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.tickers.models import Ticker, Watchlist


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
class TestWatchlist:
    def test_add_ticker_to_watchlist(self, auth_client, ticker):
        resp = auth_client.post("/api/watchlist/", {"symbol": "AAPL"})
        assert resp.status_code == 201
        assert resp.data["symbol"] == "AAPL"

    def test_list_watchlist(self, auth_client, ticker):
        auth_client.post("/api/watchlist/", {"symbol": "AAPL"})
        resp = auth_client.get("/api/watchlist/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_remove_from_watchlist(self, auth_client, ticker):
        auth_client.post("/api/watchlist/", {"symbol": "AAPL"})
        resp = auth_client.delete("/api/watchlist/AAPL/")
        assert resp.status_code == 204

    def test_watchlist_isolation(self, auth_client, ticker, db):
        other = CustomUser.objects.create_user(
            username="other", email="other@example.com", password="pass123"
        )
        Watchlist.objects.create(user=other, ticker=ticker)
        resp = auth_client.get("/api/watchlist/")
        assert len(resp.data) == 0

    def test_unauthenticated_rejected(self, ticker):
        client = APIClient()
        resp = client.get("/api/watchlist/")
        assert resp.status_code == 401

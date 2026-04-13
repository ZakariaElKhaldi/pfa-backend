import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.tickers.models import Ticker


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="test", email="test@example.com", password="pass123"
    )


@pytest.fixture
def client(user):
    c = APIClient()
    token = RefreshToken.for_user(user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.mark.django_db
def test_list_tickers_empty(client):
    response = client.get("/api/tickers/")
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_create_ticker(client):
    response = client.post("/api/tickers/", {"symbol": "AAPL", "name": "Apple Inc."})
    assert response.status_code == 201
    assert response.json()["symbol"] == "AAPL"


@pytest.mark.django_db
def test_create_ticker_duplicate_returns_400(client):
    Ticker.objects.create(symbol="AAPL")
    response = client.post("/api/tickers/", {"symbol": "AAPL"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_ticker(client):
    Ticker.objects.create(symbol="TSLA", name="Tesla")
    response = client.get("/api/tickers/TSLA/")
    assert response.status_code == 200
    assert response.json()["symbol"] == "TSLA"


@pytest.mark.django_db
def test_delete_ticker(client):
    Ticker.objects.create(symbol="GME")
    response = client.delete("/api/tickers/GME/")
    assert response.status_code == 204
    assert not Ticker.objects.filter(symbol="GME").exists()


@pytest.mark.django_db
def test_get_nonexistent_ticker_returns_404(client):
    response = client.get("/api/tickers/FAKE/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_search_tickers_by_symbol(auth_client):
    Ticker.objects.create(symbol="AAPL", name="Apple Inc.")
    Ticker.objects.create(symbol="AMZN", name="Amazon")
    response = auth_client.get("/api/tickers/?search=AAPL")
    results = response.json().get("results", response.json())
    assert len(results) == 1
    assert results[0]["symbol"] == "AAPL"


@pytest.mark.django_db
def test_search_tickers_by_name(auth_client):
    Ticker.objects.create(symbol="GOOG", name="Alphabet Inc.")
    Ticker.objects.create(symbol="MSFT", name="Microsoft Corp.")
    response = auth_client.get("/api/tickers/?search=alphabet")
    results = response.json().get("results", response.json())
    assert any(r["symbol"] == "GOOG" for r in results)

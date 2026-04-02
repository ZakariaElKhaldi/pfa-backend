import pytest
from rest_framework.test import APIClient
from apps.tickers.models import Ticker


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_list_tickers_empty(client):
    response = client.get("/tickers/")
    assert response.status_code == 200
    assert response.json()["results"] == []


@pytest.mark.django_db
def test_create_ticker(client):
    response = client.post("/tickers/", {"symbol": "AAPL", "name": "Apple Inc."})
    assert response.status_code == 201
    assert response.json()["symbol"] == "AAPL"


@pytest.mark.django_db
def test_create_ticker_duplicate_returns_400(client):
    Ticker.objects.create(symbol="AAPL")
    response = client.post("/tickers/", {"symbol": "AAPL"})
    assert response.status_code == 400


@pytest.mark.django_db
def test_get_ticker(client):
    Ticker.objects.create(symbol="TSLA", name="Tesla")
    response = client.get("/tickers/TSLA/")
    assert response.status_code == 200
    assert response.json()["symbol"] == "TSLA"


@pytest.mark.django_db
def test_delete_ticker(client):
    Ticker.objects.create(symbol="GME")
    response = client.delete("/tickers/GME/")
    assert response.status_code == 204
    assert not Ticker.objects.filter(symbol="GME").exists()


@pytest.mark.django_db
def test_get_nonexistent_ticker_returns_404(client):
    response = client.get("/tickers/FAKE/")
    assert response.status_code == 404

"""Mood timeline API tests."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.intelligence.models import MarketMoodSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="u", email="u@x.com", password="p"
    )


@pytest.fixture
def client(user):
    c = APIClient()
    token = RefreshToken.for_user(user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL", name="Apple")


@pytest.mark.django_db
def test_mood_endpoint_returns_recent_snapshots(client, ticker):
    now = timezone.now()
    for i in range(3):
        MarketMoodSnapshot.objects.create(
            ticker=ticker,
            embedding={"mean_sentiment": 0.5},
            dominant_mood="bullish",
            confidence=0.6,
            window_start=now - timedelta(hours=i + 1),
            window_end=now - timedelta(hours=i),
        )
    resp = client.get(f"/api/tickers/{ticker.symbol}/mood/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert data[0]["dominant_mood"] == "bullish"
    assert "confidence" in data[0]
    assert "window_start" in data[0]


@pytest.mark.django_db
def test_mood_endpoint_empty_returns_empty_list(client, ticker):
    resp = client.get(f"/api/tickers/{ticker.symbol}/mood/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.django_db
def test_mood_endpoint_unknown_ticker_404(client):
    resp = client.get("/api/tickers/ZZZ/mood/")
    assert resp.status_code == 404

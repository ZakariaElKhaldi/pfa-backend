import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def mkt_user(db):
    return CustomUser.objects.create_user(
        username="pricetest", email="pricetest@example.com", password="pass"
    )


@pytest.fixture
def mkt_client(mkt_user):
    c = APIClient()
    token = RefreshToken.for_user(mkt_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.mark.django_db
def test_prices_returns_local_live_history(mkt_client):
    ticker = Ticker.objects.create(symbol="PXLOCAL", name="Local")
    now = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("10.00"),
        timestamp=now - datetime.timedelta(minutes=1),
        source=PriceSnapshot.SOURCE_ALPACA_STREAM,
    )

    resp = mkt_client.get("/api/tickers/PXLOCAL/prices/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert float(resp.json()[0]["price"]) == 10.0


@pytest.mark.django_db
@patch("apps.market.views._fetch_and_store_recent_bars")
def test_prices_fetches_alpaca_history_when_no_live_rows(mock_fetch, mkt_client):
    ticker = Ticker.objects.create(symbol="PXEMPTY", name="Empty")
    now = timezone.now()

    def fetch_history(_symbol):
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal("101.00"),
            open_price=Decimal("100.00"),
            high_price=Decimal("102.00"),
            low_price=Decimal("99.00"),
            volume=500,
            timestamp=now - datetime.timedelta(minutes=2),
            source=PriceSnapshot.SOURCE_ALPACA_REST,
        )
        PriceSnapshot.objects.create(
            ticker=ticker,
            price=Decimal("103.00"),
            open_price=Decimal("101.00"),
            high_price=Decimal("104.00"),
            low_price=Decimal("100.00"),
            volume=900,
            timestamp=now - datetime.timedelta(minutes=1),
            source=PriceSnapshot.SOURCE_ALPACA_REST,
        )
        return 2

    mock_fetch.side_effect = fetch_history

    resp = mkt_client.get("/api/tickers/PXEMPTY/prices/")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert float(body[0]["price"]) == 103.0
    assert float(body[1]["price"]) == 101.0
    mock_fetch.assert_called_once_with("PXEMPTY")


@pytest.mark.django_db
@patch("apps.market.views._fetch_and_store_recent_bars")
def test_prices_ignores_seed_data_and_fetches_real_history(mock_fetch, mkt_client):
    ticker = Ticker.objects.create(symbol="PXSEED", name="Seed")
    now = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("50.00"),
        timestamp=now,
        source=PriceSnapshot.SOURCE_SEED,
    )

    mock_fetch.side_effect = lambda _symbol: PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("60.00"),
        timestamp=now,
        source=PriceSnapshot.SOURCE_ALPACA_REST,
    )

    resp = mkt_client.get("/api/tickers/PXSEED/prices/")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert float(body[0]["price"]) == 60.0
    mock_fetch.assert_called_once_with("PXSEED")

# apps/market/tests/test_quote.py
import pytest
import datetime
from decimal import Decimal
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def mkt_user(db):
    return CustomUser.objects.create_user(
        username="mkttest", email="mkttest@example.com", password="pass"
    )


@pytest.fixture
def mkt_client(mkt_user):
    c = APIClient()
    token = RefreshToken.for_user(mkt_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return c


@pytest.mark.django_db
def test_quote_returns_latest_price(mkt_client):
    ticker = Ticker.objects.create(symbol="TSLA", name="Tesla")
    PriceSnapshot.objects.create(ticker=ticker, price=Decimal("250.00"), timestamp=timezone.now())
    resp = mkt_client.get("/api/tickers/TSLA/quote/")
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 250.0


@pytest.mark.django_db
def test_quote_404_when_no_data(mkt_client):
    Ticker.objects.create(symbol="NONE", name="None")
    resp = mkt_client.get("/api/tickers/NONE/quote/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_quote_returns_most_recent(mkt_client):
    ticker = Ticker.objects.create(symbol="GOOG", name="Google")
    t1 = timezone.now()
    t0 = t1 - datetime.timedelta(hours=1)
    PriceSnapshot.objects.create(ticker=ticker, price=Decimal("100.00"), timestamp=t0)
    PriceSnapshot.objects.create(ticker=ticker, price=Decimal("120.00"), timestamp=t1)
    resp = mkt_client.get("/api/tickers/GOOG/quote/")
    assert float(resp.json()["price"]) == 120.0


@pytest.mark.django_db
def test_quote_prefers_live_source_over_seed(mkt_client):
    ticker = Ticker.objects.create(symbol="NVDA", name="NVIDIA")
    now = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("99.00"),
        timestamp=now,
        source=PriceSnapshot.SOURCE_SEED,
    )
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("120.00"),
        timestamp=now - datetime.timedelta(minutes=1),
        source=PriceSnapshot.SOURCE_ALPACA_STREAM,
    )
    resp = mkt_client.get("/api/tickers/NVDA/quote/")
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 120.0


@pytest.mark.django_db
@patch("apps.market.views._fetch_and_store_latest_bar")
def test_quote_fetches_from_alpaca_when_no_local_live_data(mock_fetch, mkt_client):
    ticker = Ticker.objects.create(symbol="ZQAMZN", name="Amazon")
    now = timezone.now()
    mock_fetch.side_effect = lambda _symbol: PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("201.25"),
        open_price=Decimal("199.00"),
        high_price=Decimal("202.00"),
        low_price=Decimal("198.50"),
        volume=12345,
        timestamp=now,
        source=PriceSnapshot.SOURCE_ALPACA_REST,
    )

    resp = mkt_client.get("/api/tickers/ZQAMZN/quote/")
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 201.25
    mock_fetch.assert_called_once_with("ZQAMZN")


@pytest.mark.django_db
@patch("apps.market.views._fetch_and_store_latest_bar")
def test_quote_refreshes_stale_live_data(mock_fetch, mkt_client):
    ticker = Ticker.objects.create(symbol="ZQMETA", name="Meta")
    stale_ts = timezone.now() - datetime.timedelta(minutes=30)
    fresh_ts = timezone.now()
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("100.00"),
        open_price=Decimal("99.00"),
        high_price=Decimal("101.00"),
        low_price=Decimal("98.00"),
        volume=1000,
        timestamp=stale_ts,
        source=PriceSnapshot.SOURCE_ALPACA_STREAM,
    )
    mock_fetch.side_effect = lambda _symbol: PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("110.00"),
        open_price=Decimal("108.00"),
        high_price=Decimal("111.00"),
        low_price=Decimal("107.00"),
        volume=4000,
        timestamp=fresh_ts,
        source=PriceSnapshot.SOURCE_ALPACA_REST,
    )

    resp = mkt_client.get("/api/tickers/ZQMETA/quote/")
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 110.0
    mock_fetch.assert_called_once_with("ZQMETA")


@pytest.mark.django_db
@patch("apps.market.views._fetch_and_store_latest_bar")
def test_quote_keeps_recent_live_data_without_refresh(mock_fetch, mkt_client):
    ticker = Ticker.objects.create(symbol="IBM", name="IBM")
    PriceSnapshot.objects.create(
        ticker=ticker,
        price=Decimal("160.00"),
        open_price=Decimal("158.00"),
        high_price=Decimal("161.00"),
        low_price=Decimal("157.00"),
        volume=800,
        timestamp=timezone.now(),
        source=PriceSnapshot.SOURCE_ALPACA_STREAM,
    )

    resp = mkt_client.get("/api/tickers/IBM/quote/")
    assert resp.status_code == 200
    assert float(resp.json()["price"]) == 160.0
    mock_fetch.assert_not_called()

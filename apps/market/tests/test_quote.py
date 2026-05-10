# apps/market/tests/test_quote.py
import pytest
import datetime
from decimal import Decimal
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

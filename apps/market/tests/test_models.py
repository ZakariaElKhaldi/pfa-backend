import pytest
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="TSLA")


@pytest.mark.django_db
def test_price_snapshot_has_ohlc_fields(ticker):
    snap = PriceSnapshot.objects.create(
        ticker=ticker,
        price="150.0000",
        open_price="148.0000",
        high_price="152.0000",
        low_price="147.5000",
        volume=500000,
        timestamp=timezone.now(),
    )
    snap.refresh_from_db()
    assert float(snap.open_price) == 148.0
    assert float(snap.high_price) == 152.0
    assert float(snap.low_price) == 147.5
    assert float(snap.price) == 150.0


@pytest.mark.django_db
def test_price_snapshot_ohlc_fields_nullable(ticker):
    snap = PriceSnapshot.objects.create(
        ticker=ticker,
        price="150.0000",
        volume=500000,
        timestamp=timezone.now(),
    )
    snap.refresh_from_db()
    assert snap.open_price is None
    assert snap.high_price is None
    assert snap.low_price is None


@pytest.mark.django_db
def test_price_snapshot_backward_compatible(ticker):
    snap = PriceSnapshot.objects.create(
        ticker=ticker,
        price="200.5000",
        volume=100000,
        timestamp=timezone.now(),
    )
    snap.refresh_from_db()
    assert float(snap.price) == 200.5
    assert snap.volume == 100000
    assert snap.source == PriceSnapshot.SOURCE_ALPACA_STREAM

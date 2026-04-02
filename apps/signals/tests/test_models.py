import pytest
from django.utils import timezone
from apps.tickers.models import Ticker
from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot, AlertFlag


@pytest.mark.django_db
def test_price_snapshot_created():
    ticker = Ticker.objects.create(symbol="NVDA")
    snap = PriceSnapshot.objects.create(
        ticker=ticker, price="500.25", volume=1000000, timestamp=timezone.now()
    )
    assert PriceSnapshot.objects.filter(ticker=ticker).count() == 1
    assert float(snap.price) == 500.25


@pytest.mark.django_db
def test_signal_snapshot_created():
    ticker = Ticker.objects.create(symbol="NVDA")
    snap = SignalSnapshot.objects.create(
        ticker=ticker,
        sentiment=0.6,
        momentum=0.4,
        consistency=0.9,
        signal=SignalSnapshot.SIGNAL_BUY,
        post_count=15,
    )
    assert snap.signal == "BUY"


@pytest.mark.django_db
def test_alert_flag_defaults_unresolved():
    ticker = Ticker.objects.create(symbol="NVDA")
    alert = AlertFlag.objects.create(
        ticker=ticker,
        type=AlertFlag.TYPE_DIVERGENCE,
        sentiment=0.8,
        momentum=-0.5,
        consistency=0.25,
    )
    assert alert.resolved is False

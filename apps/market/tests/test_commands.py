import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


@pytest.mark.django_db
def test_purge_seed_prices_dry_run_does_not_delete():
    ticker = Ticker.objects.create(symbol="AAPL", name="Apple")
    PriceSnapshot.objects.create(
        ticker=ticker,
        price="100.0",
        volume=1000,
        timestamp=timezone.now(),
        source=PriceSnapshot.SOURCE_SEED,
    )
    call_command("purge_seed_prices", "--dry-run")
    assert PriceSnapshot.objects.filter(source=PriceSnapshot.SOURCE_SEED).count() == 1


@pytest.mark.django_db
def test_purge_seed_prices_deletes_only_seed_rows():
    ticker = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    PriceSnapshot.objects.create(
        ticker=ticker,
        price="100.0",
        volume=1000,
        timestamp=timezone.now(),
        source=PriceSnapshot.SOURCE_SEED,
    )
    PriceSnapshot.objects.create(
        ticker=ticker,
        price="200.0",
        volume=2000,
        timestamp=timezone.now(),
        source=PriceSnapshot.SOURCE_ALPACA_STREAM,
    )

    call_command("purge_seed_prices")

    assert PriceSnapshot.objects.filter(source=PriceSnapshot.SOURCE_SEED).count() == 0
    assert PriceSnapshot.objects.filter(source=PriceSnapshot.SOURCE_ALPACA_STREAM).count() == 1

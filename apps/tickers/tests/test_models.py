import pytest

from apps.tickers.models import Ticker


@pytest.mark.django_db
def test_ticker_has_sector_field():
    t = Ticker.objects.create(symbol="AAPL", name="Apple", sector="Technology")
    assert t.sector == "Technology"


@pytest.mark.django_db
def test_ticker_sector_defaults_blank():
    t = Ticker.objects.create(symbol="MSFT", name="Microsoft")
    assert t.sector == ""

import pytest
from unittest.mock import patch, MagicMock, call
from decimal import Decimal
from django.utils import timezone
from apps.tickers.models import Ticker
from apps.market.models import PriceSnapshot
from apps.market.alpaca_stream import AlpacaStreamManager


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


@pytest.mark.django_db
@patch("apps.market.alpaca_stream.push_market_update")
def test_handle_bar_stores_price_snapshot(mock_push, ticker):
    manager = AlpacaStreamManager()
    bar = MagicMock()
    bar.symbol = "AAPL"
    bar.close = Decimal("155.50")
    bar.volume = 5000000
    bar.timestamp = timezone.now()

    manager.handle_bar(bar)

    snap = PriceSnapshot.objects.get(ticker=ticker)
    assert snap.price == Decimal("155.50")
    mock_push.assert_called_once()
    call_args = mock_push.call_args[0]
    assert call_args[0] == "AAPL"
    assert call_args[1]["type"] == "price"


@pytest.mark.django_db
def test_handle_bar_ignores_untracked_ticker():
    manager = AlpacaStreamManager()
    bar = MagicMock()
    bar.symbol = "UNKNOWN"
    bar.close = Decimal("100.00")
    bar.volume = 0
    bar.timestamp = timezone.now()

    # Should not raise
    manager.handle_bar(bar)
    assert PriceSnapshot.objects.count() == 0


@pytest.mark.django_db
def test_get_symbols_returns_tracked_tickers(ticker):
    Ticker.objects.create(symbol="TSLA")
    manager = AlpacaStreamManager()
    symbols = manager.get_symbols()
    assert "AAPL" in symbols
    assert "TSLA" in symbols

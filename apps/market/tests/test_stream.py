from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.market.alpaca_stream import AlpacaStreamManager
from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def ticker(db):
    return Ticker.objects.create(symbol="AAPL")


@pytest.mark.django_db
@patch("apps.market.alpaca_stream.push_market_update")
def test_handle_bar_stores_price_snapshot(mock_push, ticker):
    manager = AlpacaStreamManager()
    bar = MagicMock()
    bar.symbol = "AAPL"
    bar.open = Decimal("153.00")
    bar.high = Decimal("156.00")
    bar.low = Decimal("152.00")
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


@pytest.mark.django_db
@patch("apps.market.alpaca_stream.push_market_update")
def test_handle_bar_stores_ohlc_fields(mock_push, ticker):
    manager = AlpacaStreamManager()
    bar = MagicMock()
    bar.symbol = "AAPL"
    bar.open = Decimal("150.00")
    bar.high = Decimal("156.00")
    bar.low = Decimal("149.50")
    bar.close = Decimal("155.50")
    bar.volume = 5000000
    bar.timestamp = timezone.now()

    manager.handle_bar(bar)

    snap = PriceSnapshot.objects.get(ticker=ticker)
    assert snap.price == Decimal("155.50")
    assert snap.open_price == Decimal("150.00")
    assert snap.high_price == Decimal("156.00")
    assert snap.low_price == Decimal("149.50")


@pytest.mark.django_db
@patch("apps.market.alpaca_stream.push_market_update")
def test_handle_bar_pushes_ohlc_in_websocket(mock_push, ticker):
    manager = AlpacaStreamManager()
    bar = MagicMock()
    bar.symbol = "AAPL"
    bar.open = Decimal("150.00")
    bar.high = Decimal("156.00")
    bar.low = Decimal("149.50")
    bar.close = Decimal("155.50")
    bar.volume = 5000000
    bar.timestamp = timezone.now()

    manager.handle_bar(bar)

    payload = mock_push.call_args[0][1]
    assert payload["open"] == "150.00"
    assert payload["high"] == "156.00"
    assert payload["low"] == "149.50"

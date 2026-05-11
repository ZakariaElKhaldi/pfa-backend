import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from asgiref.sync import async_to_sync
from apps.market.alpaca_stream import AlpacaStreamManager
from apps.tickers.models import Ticker
from apps.market.models import ActiveMarketSubscription, PriceSnapshot, TradeTick

@pytest.mark.django_db
class TestAlpacaStreamLogic:
    @patch("apps.market.alpaca_stream.push_market_update")
    def test_handle_bar(self, mock_push):
        # Setup ticker
        ticker = Ticker.objects.create(symbol="AAPL")
        
        # Mock bar object
        mock_bar = MagicMock()
        mock_bar.symbol = "AAPL"
        mock_bar.open = 150.0
        mock_bar.high = 155.0
        mock_bar.low = 149.0
        mock_bar.close = 152.0
        mock_bar.volume = 1000
        mock_bar.timestamp = datetime.now(tz=timezone.utc)
        
        manager = AlpacaStreamManager()
        async_to_sync(manager.handle_bar)(mock_bar)
        
        # Verify database record
        snapshot = PriceSnapshot.objects.get(ticker=ticker)
        assert float(snapshot.price) == 152.0
        assert float(snapshot.open_price) == 150.0
        assert snapshot.source == PriceSnapshot.SOURCE_ALPACA_STREAM
        
        # Verify WebSocket push
        mock_push.assert_called_once()
        args, kwargs = mock_push.call_args
        assert args[0] == "AAPL"
        assert args[1]["type"] == "price"
        assert args[1]["price"] == "152.0"

    @patch("alpaca.data.live.StockDataStream")
    def test_run_reconnect_loop(self, mock_stream_class):
        # Mock the stream instance
        mock_stream = MagicMock()
        mock_stream_class.return_value = mock_stream
        
        manager = AlpacaStreamManager()
        
        with patch.object(manager, "get_active_symbols") as mock_get_symbols:
            # First call returns AAPL, second call raises StopIteration to break our manual test
            mock_get_symbols.side_effect = [["AAPL"], StopIteration("Break loop")]
            
            # Make stream.run fail to verify the catch block
            mock_stream.run.side_effect = Exception("Alpaca Error")
            
            with patch("time.sleep", return_value=None): 
                with patch("apps.market.alpaca_stream.logger") as mock_logger:
                    try:
                        manager.run()
                    except StopIteration:
                        pass # Normal break for test
            
            # Verify it logged the error from stream.run
            mock_logger.error.assert_any_call("Alpaca stream error: %s. Reconnecting in 10s.", mock_stream.run.side_effect)
            # Verify subscribe_trades was called before run
            mock_stream.subscribe_trades.assert_called_with(manager.handle_trade, "AAPL")

    @patch("apps.market.alpaca_stream.push_market_update")
    def test_handle_trade_persists_tick_and_updates_minute_bar(self, mock_push):
        ticker = Ticker.objects.create(symbol="AAPL")
        manager = AlpacaStreamManager()

        first = MagicMock()
        first.symbol = "AAPL"
        first.price = 152.0
        first.size = 100
        first.exchange = "V"
        first.id = "t1"
        first.conditions = ["@"]
        first.timestamp = datetime(2026, 5, 11, 14, 31, 10, tzinfo=timezone.utc)

        second = MagicMock()
        second.symbol = "AAPL"
        second.price = 153.5
        second.size = 50
        second.exchange = "V"
        second.id = "t2"
        second.conditions = []
        second.timestamp = datetime(2026, 5, 11, 14, 31, 20, tzinfo=timezone.utc)

        async_to_sync(manager.handle_trade)(first)
        async_to_sync(manager.handle_trade)(second)

        assert TradeTick.objects.filter(ticker=ticker).count() == 2
        snapshot = PriceSnapshot.objects.get(ticker=ticker)
        assert float(snapshot.open_price) == 152.0
        assert float(snapshot.high_price) == 153.5
        assert float(snapshot.low_price) == 152.0
        assert float(snapshot.price) == 153.5
        assert snapshot.volume == 150

        payload = mock_push.call_args[0][1]
        assert payload["type"] == "trade"
        assert payload["price"] == "153.5"
        assert payload["close"] == "153.5"
        assert payload["bar_timestamp"].endswith("14:31:00+00:00")

    def test_get_active_symbols_removes_expired_subscriptions(self):
        now = datetime.now(tz=timezone.utc)
        ActiveMarketSubscription.objects.create(
            symbol="AAPL",
            channel_name="fresh",
            expires_at=now + timedelta(minutes=1),
        )
        ActiveMarketSubscription.objects.create(
            symbol="MSFT",
            channel_name="expired",
            expires_at=now - timedelta(minutes=1),
        )

        manager = AlpacaStreamManager()

        assert manager.get_active_symbols() == ["AAPL"]
        assert not ActiveMarketSubscription.objects.filter(symbol="MSFT").exists()

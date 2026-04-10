import json
from unittest.mock import MagicMock, patch

from apps.events.bus import publish
from apps.events.types import SIGNAL_GENERATED


class TestEventBus:
    @patch("apps.events.bus._get_redis")
    def test_publish_sends_to_redis(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        publish(SIGNAL_GENERATED, {"ticker": "AAPL", "signal": "BUY"})

        mock_redis.publish.assert_called_once()
        channel, message = mock_redis.publish.call_args[0]
        assert channel == f"crowdsignal:{SIGNAL_GENERATED}"
        data = json.loads(message)
        assert data["type"] == SIGNAL_GENERATED
        assert data["payload"]["ticker"] == "AAPL"

    @patch("apps.events.bus._get_redis")
    def test_publish_includes_timestamp(self, mock_get_redis):
        mock_redis = MagicMock()
        mock_get_redis.return_value = mock_redis

        publish(SIGNAL_GENERATED, {"ticker": "AAPL"})

        _, message = mock_redis.publish.call_args[0]
        data = json.loads(message)
        assert "timestamp" in data

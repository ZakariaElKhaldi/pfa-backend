import logging

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def push_market_update(ticker_symbol: str, data: dict) -> None:
    """Push a market update to all WebSocket clients subscribed to this ticker."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"market_{ticker_symbol}",
            {"type": "market.update", "data": data},
        )
    except Exception as e:
        logger.error("WebSocket push failed for %s: %s", ticker_symbol, e)

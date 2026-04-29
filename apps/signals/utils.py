"""Signal WebSocket broadcast helpers."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

SIGNALS_GROUP = "signals_global"


def push_signal_update(data: dict) -> None:
    """Broadcast a signal update to all ws/signals/ subscribers."""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            SIGNALS_GROUP,
            {"type": "signal.new", "data": data},
        )
    except Exception as exc:
        logger.error("Signal WebSocket push failed: %s", exc)

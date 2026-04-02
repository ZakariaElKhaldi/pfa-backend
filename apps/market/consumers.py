import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class MarketConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.ticker = self.scope["url_route"]["kwargs"]["ticker"].upper()
        self.group_name = f"market_{self.ticker}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("WS connected: %s", self.ticker)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("WS disconnected: %s (code=%s)", self.ticker, close_code)

    async def market_update(self, event):
        """Called when group_send sends type='market.update'"""
        await self.send_json(event["data"])

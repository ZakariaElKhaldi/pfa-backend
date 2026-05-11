import logging
import datetime
import asyncio

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings
from django.db import connection
from django.utils import timezone

from .models import ActiveMarketSubscription

logger = logging.getLogger(__name__)

SUBSCRIPTION_TTL_SECONDS = 90


class MarketConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.ticker = self.scope["url_route"]["kwargs"]["ticker"].upper()
        self.group_name = f"market_{self.ticker}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        self.subscription_task = None
        if not self._skip_registry_for_tests():
            self.subscription_task = asyncio.create_task(self._register_subscription())
        logger.debug("WS connected: %s", self.ticker)

    async def disconnect(self, close_code):
        task = getattr(self, "subscription_task", None)
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=1)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()
        if not self._skip_registry_for_tests():
            await self._unregister_subscription()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("WS disconnected: %s (code=%s)", self.ticker, close_code)

    async def market_update(self, event):
        """Called when group_send sends type='market.update'"""
        await self.send_json(event["data"])

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "heartbeat":
            if not self._skip_registry_for_tests():
                await self._extend_subscription()

    @sync_to_async(thread_sensitive=False)
    def _register_subscription(self):
        if self._skip_threaded_registry_for_memory_tests():
            return
        now = timezone.now()
        ActiveMarketSubscription.objects.update_or_create(
            channel_name=self.channel_name,
            defaults={
                "symbol": self.ticker,
                "connected_at": now,
                "expires_at": now + datetime.timedelta(seconds=SUBSCRIPTION_TTL_SECONDS),
            },
        )

    @sync_to_async(thread_sensitive=False)
    def _unregister_subscription(self):
        if self._skip_threaded_registry_for_memory_tests():
            return
        ActiveMarketSubscription.objects.filter(channel_name=self.channel_name).delete()

    @sync_to_async(thread_sensitive=False)
    def _extend_subscription(self):
        if self._skip_threaded_registry_for_memory_tests():
            return
        ActiveMarketSubscription.objects.filter(channel_name=self.channel_name).update(
            expires_at=timezone.now() + datetime.timedelta(seconds=SUBSCRIPTION_TTL_SECONDS)
        )

    @staticmethod
    def _skip_threaded_registry_for_memory_tests():
        return str(connection.settings_dict.get("NAME", "")).startswith("file:memorydb_")

    @staticmethod
    def _skip_registry_for_tests():
        return getattr(settings, "TESTING", False)

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SignalConsumer(AsyncJsonWebsocketConsumer):
    GROUP_NAME = "signals_global"

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def signal_new(self, event):
        await self.send_json(event["data"])

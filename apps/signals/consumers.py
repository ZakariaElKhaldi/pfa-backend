from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class SignalConsumer(AsyncJsonWebsocketConsumer):
    GROUP_NAME = "signals_global"

    @staticmethod
    @sync_to_async
    def _user_from_token(token: str):
        auth = JWTStatelessUserAuthentication()
        validated = auth.get_validated_token(token)
        return auth.get_user(validated)

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            query_string = self.scope.get("query_string", b"").decode()
            token = (parse_qs(query_string).get("token") or [None])[0]
            if token:
                try:
                    user = await self._user_from_token(token)
                    self.scope["user"] = user
                except (InvalidToken, TokenError, ValueError):
                    user = None
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)

    async def signal_new(self, event):
        await self.send_json(event["data"])

from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def _get_user_from_token(token: str):
    auth = JWTStatelessUserAuthentication()
    validated = auth.get_validated_token(token)
    return auth.get_user(validated)


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket JWT auth for Channels.
    Supports access token via query param: ?token=<jwt>
    """

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = (params.get("token") or [None])[0]
        scope["user"] = AnonymousUser()

        if token:
            try:
                scope["user"] = await _get_user_from_token(token)
            except (InvalidToken, TokenError, ValueError):
                scope["user"] = AnonymousUser()
            except Exception:
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)

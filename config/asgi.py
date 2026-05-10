import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

django_asgi_app = get_asgi_application()

# Import modules that depend on loaded Django apps only after setup.
from apps.accounts.ws_auth import JWTAuthMiddlewareStack  # noqa: E402
import apps.market.routing  # noqa: E402
import apps.signals.routing  # noqa: E402

websocket_application = JWTAuthMiddlewareStack(
    URLRouter(
        apps.market.routing.websocket_urlpatterns
        + apps.signals.routing.websocket_urlpatterns
    )
)

websocket_application = AllowedHostsOriginValidator(websocket_application)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": websocket_application,
    }
)

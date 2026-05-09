import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")

# Import routing after env is set
import apps.market.routing  # noqa: E402
import apps.signals.routing  # noqa: E402

websocket_application = AuthMiddlewareStack(
    URLRouter(
        apps.market.routing.websocket_urlpatterns
        + apps.signals.routing.websocket_urlpatterns
    )
)

if not getattr(settings, "TESTING", False):
    websocket_application = AllowedHostsOriginValidator(websocket_application)

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": websocket_application,
    }
)

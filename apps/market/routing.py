from django.urls import re_path
from .consumers import MarketConsumer

websocket_urlpatterns = [
    re_path(r"ws/market/(?P<ticker>[A-Z]+)/$", MarketConsumer.as_asgi()),
]

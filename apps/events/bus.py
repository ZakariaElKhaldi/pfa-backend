import json
import logging

import redis
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    return _redis_client


def publish(event_type: str, payload: dict):
    """Publish an event to the Redis channel."""
    message = json.dumps({
        "type": event_type,
        "payload": payload,
        "timestamp": now().isoformat(),
    })
    try:
        _get_redis().publish(f"crowdsignal:{event_type}", message)
    except Exception as e:
        logger.exception("Failed to publish event %s: %s", event_type, e)

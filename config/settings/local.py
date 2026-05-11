"""
config/settings/local.py — Local dev overrides
Extends base.py with SQLite, conditional Redis channel layer, and LocMem cache
so Django can run lightweight locally while still supporting cross-process
WebSockets when REDIS_HOST is set.

Usage:
  set DJANGO_SETTINGS_MODULE=config.settings.local
  python manage.py runserver
"""
from .base import *  # noqa: F401, F403

# Use SQLite locally — no PostgreSQL required
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "local_dev.sqlite3",
    }
}

_local_redis_host = config("REDIS_HOST", default="")

# Use Redis when configured so Daphne and stream daemons can share WebSocket groups.
# InMemory remains available for quick single-process API work, but it cannot deliver
# market updates across separate backend processes.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(_local_redis_host, 6379)],
        },
    }
    if _local_redis_host
    else {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Use Django's built-in LocMem cache (no Redis needed)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Keep Celery asynchronous in local dev by default. Set CELERY_TASK_ALWAYS_EAGER=True
# explicitly when debugging a task inline without a worker.
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER

# Allow all API requests without auth in local dev
REST_FRAMEWORK = {
    **globals().get('REST_FRAMEWORK', {}),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}

# Allow all CORS origins in dev
CORS_ALLOW_ALL_ORIGINS = True

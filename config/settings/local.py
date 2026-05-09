"""
config/settings/local.py — Local dev overrides
Extends base.py with InMemory channel layer + LocMem cache
so Django runs without Redis or PostgreSQL for quick dev/UI review.

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

# Use InMemory channel layer (no Redis needed)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# Use Django's built-in LocMem cache (no Redis needed)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery task execution locally (tasks queued but not run)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

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

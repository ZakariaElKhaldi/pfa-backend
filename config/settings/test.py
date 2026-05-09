from .base import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Use a file-based sqlite DB for local test runs so migrations persist
        # across separate manage.py invocations (in-memory DB is per-process).
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ratelimit-test",
    }
}

# Disable rate limiting in tests
RATELIMIT_ENABLE = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Allow frontend dev servers to call the test backend without CORS issues.
# For local development only.
CORS_ALLOW_ALL_ORIGINS = True

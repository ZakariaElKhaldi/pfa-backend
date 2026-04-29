from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=[("user", "User"), ("analyst", "Analyst"), ("admin", "Admin")],
        default="user",
    )
    # RBAC scaffold — not enforced in MVP
    permissions = models.JSONField(default=list, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class APIKey(models.Model):
    """
    POST-MVP: API key authentication for programmatic access.
    TODO:
    - Add APIKeyAuthentication backend in accounts/backends.py
    - Add key generation endpoint: POST /api/auth/api-keys/
    - Add key revocation endpoint: DELETE /api/auth/api-keys/{id}/
    - Add scope enforcement middleware checking key.scopes against view requirements
    - Scopes: signals.read, alerts.read, export.read, market.read, portfolio.read, portfolio.write
    """

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="api_keys")
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100)
    scopes = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.user.email})"

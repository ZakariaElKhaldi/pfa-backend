from django.conf import settings
from rest_framework.permissions import BasePermission

from .models import APIKey


class IsAdmin(BasePermission):
    """Allows access only to users with role='admin'."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsAnalyst(BasePermission):
    """Allows access only to users with role='analyst'."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "analyst"


class IsAnalystOrAdmin(BasePermission):
    """Allows access to users with role='analyst' or role='admin'."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ("analyst", "admin")
        )


class HasPermission(BasePermission):
    """
    RBAC scaffold — checks user.permissions JSONField.
    POST-MVP: Enforce this on views alongside API key scope checks.
    Usage: HasPermission("signals.read")
    """

    def __init__(self, required_scope=None):
        self.required_scope = required_scope

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return self.required_scope in (request.user.permissions or [])


class ScopedAPIKeyPermission(BasePermission):
    """
    Enforce view.required_scopes when request uses API key auth.
    JWT-authenticated users continue through regular RBAC rules.
    """

    def has_permission(self, request, view):
        required_scopes = getattr(view, "required_scopes", None) or []
        if not required_scopes:
            return True

        if isinstance(request.auth, APIKey):
            key_scopes = request.auth.scopes or []
            return any(scope in key_scopes for scope in required_scopes)
        return True


class ScopedUserPermission(BasePermission):
    """
    Optional JWT-user scope enforcement.
    Controlled by settings.ENFORCE_USER_SCOPE_PERMISSIONS.
    """

    def has_permission(self, request, view):
        if not getattr(settings, "ENFORCE_USER_SCOPE_PERMISSIONS", False):
            return True

        required_scopes = getattr(view, "required_scopes", None) or []
        if not required_scopes:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "role", None) == "admin":
            return True

        user_scopes = request.user.permissions or []
        return any(scope in user_scopes for scope in required_scopes)

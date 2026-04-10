from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allows access only to users with role='admin'."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


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

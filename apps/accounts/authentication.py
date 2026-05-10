from django.utils import timezone
from rest_framework import authentication
from rest_framework import exceptions

from .models import APIKey


class APIKeyAuthentication(authentication.BaseAuthentication):
    """
    Supports either:
    - Authorization: ApiKey <key>
    - X-API-Key: <key>
    """

    keyword = "ApiKey"

    def authenticate(self, request):
        key = self._extract_key(request)
        if not key:
            return None

        api_key = (
            APIKey.objects
            .select_related("user")
            .filter(key=key, is_active=True)
            .first()
        )
        if api_key is None:
            raise exceptions.AuthenticationFailed("Invalid API key.")

        if api_key.expires_at and api_key.expires_at <= timezone.now():
            raise exceptions.AuthenticationFailed("API key expired.")

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=["last_used_at"])
        return (api_key.user, api_key)

    def _extract_key(self, request) -> str | None:
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == self.keyword.lower():
                return parts[1]
            if parts and parts[0].lower() == self.keyword.lower():
                raise exceptions.AuthenticationFailed("Invalid API key header format.")

        x_api_key = request.META.get("HTTP_X_API_KEY")
        if x_api_key:
            return x_api_key.strip()
        return None

    def authenticate_header(self, request):
        return self.keyword

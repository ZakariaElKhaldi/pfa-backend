import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser


@pytest.mark.django_db
class TestPermissions:
    def test_authenticated_user_can_access_protected_endpoint(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123"
        )
        client = APIClient()
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        resp = client.get("/api/tickers/")
        assert resp.status_code == 200

    def test_unauthenticated_user_rejected(self):
        client = APIClient()
        resp = client.get("/api/tickers/")
        assert resp.status_code == 401

    def test_regular_user_cannot_resolve_alerts(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123", role="user"
        )
        client = APIClient()
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        resp = client.patch("/api/alerts/999/resolve/")
        assert resp.status_code == 403

    def test_admin_can_access_audit(self):
        admin = CustomUser.objects.create_user(
            username="admin", email="admin@example.com", password="pass123", role="admin"
        )
        client = APIClient()
        token = RefreshToken.for_user(admin)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        resp = client.get("/api/audit/decisions/")
        assert resp.status_code == 200

    def test_regular_user_cannot_access_audit(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123", role="user"
        )
        client = APIClient()
        token = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        resp = client.get("/api/audit/decisions/")
        assert resp.status_code == 403

    def test_jwt_refresh_works(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123"
        )
        refresh = RefreshToken.for_user(user)
        client = APIClient()
        resp = client.post("/api/auth/token/refresh/", {"refresh": str(refresh)})
        assert resp.status_code == 200
        assert "access" in resp.data

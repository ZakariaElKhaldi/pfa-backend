import pytest
from django.core import mail


@pytest.mark.django_db
class TestPasswordEndpointsRouting:
    """Verify dj_rest_auth password routes are wired."""

    def test_password_change_url_resolves(self, auth_client):
        response = auth_client.post("/api/auth/password/change/", {})
        assert response.status_code in (400, 401)

    def test_password_reset_url_resolves(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post("/api/auth/password/reset/", {"email": "x@y.com"})
        assert response.status_code == 200

    def test_password_reset_email_uses_frontend_confirm_url(self, settings, user):
        from rest_framework.test import APIClient

        settings.FRONTEND_URL = "http://localhost:5174"
        response = APIClient().post(
            "/api/auth/password/reset/",
            {"email": user.email},
            format="json",
        )

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        body = mail.outbox[0].body
        assert "http://localhost:5174/password/reset/confirm?uid=" in body
        assert "&token=" in body

    def test_password_reset_confirm_url_resolves(self):
        from rest_framework.test import APIClient
        client = APIClient()
        response = client.post(
            "/api/auth/password/reset/confirm/",
            {"new_password1": "x", "new_password2": "x", "uid": "x", "token": "x"},
        )
        assert response.status_code in (400, 200)

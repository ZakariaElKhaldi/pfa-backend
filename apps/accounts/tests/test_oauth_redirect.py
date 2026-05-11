from urllib.parse import parse_qs, urlparse

from django.test import override_settings
from rest_framework.test import APIClient


def _social_providers(google_client_id="", google_client_secret=""):
    return {
        "github": {
            "APP": {
                "client_id": "",
                "secret": "",
            },
            "SCOPE": ["read:user", "user:email"],
        },
        "google": {
            "APP": {
                "client_id": google_client_id,
                "secret": google_client_secret,
            },
            "SCOPE": ["profile", "email"],
        },
    }


@override_settings(
    FRONTEND_URL="http://localhost:5174",
    SOCIALACCOUNT_PROVIDERS=_social_providers("google-client-id", "google-client-secret"),
)
def test_google_redirect_uses_frontend_callback_uri():
    response = APIClient().get("/api/auth/google/redirect/")

    assert response.status_code == 302
    location = response["Location"]
    parsed = urlparse(location)
    params = parse_qs(parsed.query)

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert params["client_id"] == ["google-client-id"]
    assert params["redirect_uri"] == ["http://localhost:5174/auth/callback/google"]


@override_settings(
    FRONTEND_URL="http://localhost:5174",
    SOCIALACCOUNT_PROVIDERS=_social_providers("", ""),
)
def test_google_redirect_reports_missing_oauth_config():
    response = APIClient().get("/api/auth/google/redirect/")

    assert response.status_code == 500
    assert "Google OAuth is not configured" in response.data["detail"]
    assert "http://localhost:5174/auth/callback/google" in response.data["detail"]

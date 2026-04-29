import pytest

from apps.accounts.models import CustomUser, UserPreference


@pytest.mark.django_db
class TestUserPreferenceModel:
    def test_default_values(self):
        user = CustomUser.objects.create_user(
            username="u1", email="u1@x.com", password="p"
        )
        pref = UserPreference.objects.create(user=user)
        assert pref.theme == "system"
        assert pref.default_ticker == ""
        assert pref.alert_email is True
        assert pref.alert_push is True
        assert pref.digest_frequency == "off"

    def test_one_to_one_with_user(self):
        user = CustomUser.objects.create_user(
            username="u2", email="u2@x.com", password="p"
        )
        UserPreference.objects.create(user=user)
        with pytest.raises(Exception):
            UserPreference.objects.create(user=user)


@pytest.mark.django_db
class TestUserPreferenceEndpoint:
    URL = "/api/auth/preferences/"

    def test_anon_get_returns_401(self):
        from rest_framework.test import APIClient
        response = APIClient().get(self.URL)
        assert response.status_code == 401

    def test_auth_get_autocreates_default_row(self, auth_client, user):
        response = auth_client.get(self.URL)
        assert response.status_code == 200
        assert response.json() == {
            "theme": "system",
            "default_ticker": "",
            "alert_email": True,
            "alert_push": True,
            "digest_frequency": "off",
        }
        assert UserPreference.objects.filter(user=user).exists()

    def test_patch_updates_fields(self, auth_client, user):
        UserPreference.objects.create(user=user)
        response = auth_client.patch(
            self.URL, {"theme": "dark", "default_ticker": "AAPL"}, format="json"
        )
        assert response.status_code == 200
        assert response.json()["theme"] == "dark"
        assert response.json()["default_ticker"] == "AAPL"

    def test_patch_invalid_theme_returns_400(self, auth_client, user):
        UserPreference.objects.create(user=user)
        response = auth_client.patch(self.URL, {"theme": "neon"}, format="json")
        assert response.status_code == 400
        assert "theme" in response.json()

    def test_patch_invalid_digest_returns_400(self, auth_client, user):
        UserPreference.objects.create(user=user)
        response = auth_client.patch(
            self.URL, {"digest_frequency": "monthly"}, format="json"
        )
        assert response.status_code == 400

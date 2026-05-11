import pytest


@pytest.mark.django_db
class TestUserProfileEndpoint:
    URL = "/api/auth/user/"

    def test_get_includes_profile_name_fields(self, auth_client, user):
        user.first_name = "Test"
        user.last_name = "User"
        user.save(update_fields=["first_name", "last_name"])

        response = auth_client.get(self.URL)

        assert response.status_code == 200
        assert response.json()["first_name"] == "Test"
        assert response.json()["last_name"] == "User"

    def test_patch_updates_profile_name_fields(self, auth_client, user):
        response = auth_client.patch(
            self.URL,
            {"first_name": "Ada", "last_name": "Lovelace"},
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.first_name == "Ada"
        assert user.last_name == "Lovelace"

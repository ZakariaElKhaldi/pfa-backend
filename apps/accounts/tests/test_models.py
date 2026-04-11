import pytest
from apps.accounts.models import CustomUser, APIKey


@pytest.mark.django_db
class TestCustomUser:
    def test_create_user(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123"
        )
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.permissions == []

    def test_username_field_is_email(self):
        assert CustomUser.USERNAME_FIELD == "email"

    def test_default_role_is_user(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123"
        )
        assert user.role == "user"

    def test_admin_role(self):
        user = CustomUser.objects.create_user(
            username="admin", email="admin@example.com", password="pass123", role="admin"
        )
        assert user.role == "admin"


@pytest.mark.django_db
class TestAPIKey:
    def test_create_api_key(self):
        user = CustomUser.objects.create_user(
            username="test", email="test@example.com", password="pass123"
        )
        key = APIKey.objects.create(
            user=user, key="abc123", name="My Key", scopes=["signals.read"]
        )
        assert key.is_active is True
        assert key.scopes == ["signals.read"]

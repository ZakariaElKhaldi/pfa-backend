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

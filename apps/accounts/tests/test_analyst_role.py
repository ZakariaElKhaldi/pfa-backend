"""Analyst role + IsAnalyst / IsAnalystOrAdmin permission classes."""

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.models import CustomUser


@pytest.mark.django_db
class TestAnalystRole:
    def test_role_field_choices_include_analyst(self):
        choices = dict(CustomUser._meta.get_field("role").choices)
        assert "analyst" in choices
        assert choices["analyst"] == "Analyst"

    def test_create_user_with_analyst_role(self):
        user = CustomUser.objects.create_user(
            username="ana", email="ana@example.com", password="pass123", role="analyst"
        )
        assert user.role == "analyst"


@pytest.mark.django_db
class TestIsAnalystPermission:
    def setup_method(self):
        from apps.accounts.permissions import IsAnalyst

        self.perm = IsAnalyst()
        self.factory = APIRequestFactory()

    def _req_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_grants_analyst_role(self):
        user = CustomUser.objects.create_user(
            username="a", email="a@e.com", password="x", role="analyst"
        )
        assert self.perm.has_permission(self._req_for(user), None) is True

    def test_denies_user_role(self):
        user = CustomUser.objects.create_user(
            username="u", email="u@e.com", password="x", role="user"
        )
        assert self.perm.has_permission(self._req_for(user), None) is False

    def test_denies_admin_role(self):
        user = CustomUser.objects.create_user(
            username="ad", email="ad@e.com", password="x", role="admin"
        )
        assert self.perm.has_permission(self._req_for(user), None) is False

    def test_denies_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser

        assert self.perm.has_permission(self._req_for(AnonymousUser()), None) is False


@pytest.mark.django_db
class TestIsAnalystOrAdminPermission:
    def setup_method(self):
        from apps.accounts.permissions import IsAnalystOrAdmin

        self.perm = IsAnalystOrAdmin()
        self.factory = APIRequestFactory()

    def _req_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_grants_analyst(self):
        user = CustomUser.objects.create_user(
            username="a", email="a@e.com", password="x", role="analyst"
        )
        assert self.perm.has_permission(self._req_for(user), None) is True

    def test_grants_admin(self):
        user = CustomUser.objects.create_user(
            username="ad", email="ad@e.com", password="x", role="admin"
        )
        assert self.perm.has_permission(self._req_for(user), None) is True

    def test_denies_user_role(self):
        user = CustomUser.objects.create_user(
            username="u", email="u@e.com", password="x", role="user"
        )
        assert self.perm.has_permission(self._req_for(user), None) is False

    def test_denies_unauthenticated(self):
        from django.contrib.auth.models import AnonymousUser

        assert self.perm.has_permission(self._req_for(AnonymousUser()), None) is False

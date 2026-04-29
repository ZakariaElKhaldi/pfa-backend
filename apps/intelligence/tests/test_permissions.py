import pytest


@pytest.mark.django_db
class TestManipulationFlagListPerms:
    URL = "/api/intelligence/flags/"

    def test_anon_401(self):
        from rest_framework.test import APIClient
        assert APIClient().get(self.URL).status_code == 401

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 200

    def test_admin_200(self, admin_client):
        assert admin_client.get(self.URL).status_code == 200


@pytest.mark.django_db
class TestRetrainLogListPerms:
    URL = "/api/intelligence/retrain-logs/"

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client):
        assert analyst_client.get(self.URL).status_code == 200

    def test_admin_200(self, admin_client):
        assert admin_client.get(self.URL).status_code == 200


@pytest.mark.django_db
class TestManipulationFlagReviewStaysAdminOnly:
    """Mutating action stays admin-only."""

    def _url(self, pk):
        return f"/api/intelligence/flags/{pk}/review/"

    def test_analyst_403(self, analyst_client, ticker):
        from apps.intelligence.models import ManipulationFlag
        flag = ManipulationFlag.objects.create(
            ticker=ticker, pattern_type="bot_swarm",
            confidence=0.9, evidence={},
        )
        assert analyst_client.patch(self._url(flag.pk)).status_code == 403

    def test_admin_200(self, admin_client, ticker):
        from apps.intelligence.models import ManipulationFlag
        flag = ManipulationFlag.objects.create(
            ticker=ticker, pattern_type="bot_swarm",
            confidence=0.9, evidence={},
        )
        assert admin_client.patch(self._url(flag.pk)).status_code == 200

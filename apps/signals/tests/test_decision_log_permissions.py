import pytest

from apps.signals.models import DecisionLog, SignalSnapshot


@pytest.mark.django_db
class TestDecisionLogListPerms:
    URL = "/api/audit/decisions/"

    def _seed(self, ticker):
        snap = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.1, momentum=0.0,
            consistency=0.5, signal="HOLD", post_count=10,
        )
        return DecisionLog.objects.create(
            signal_snapshot=snap, ticker=ticker,
            input_summary={}, scoring_detail={}, engine_output={},
        )

    def test_anon_401(self):
        from rest_framework.test import APIClient
        assert APIClient().get(self.URL).status_code == 401

    def test_user_403(self, auth_client):
        assert auth_client.get(self.URL).status_code == 403

    def test_analyst_200(self, analyst_client, ticker):
        self._seed(ticker)
        assert analyst_client.get(self.URL).status_code == 200

    def test_admin_200(self, admin_client, ticker):
        self._seed(ticker)
        assert admin_client.get(self.URL).status_code == 200


@pytest.mark.django_db
class TestDecisionLogDetailPerms:
    def test_analyst_200(self, analyst_client, ticker):
        snap = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.0, momentum=0.0,
            consistency=0.0, signal="HOLD", post_count=0,
        )
        log = DecisionLog.objects.create(
            signal_snapshot=snap, ticker=ticker,
            input_summary={}, scoring_detail={}, engine_output={},
        )
        assert analyst_client.get(f"/api/audit/decisions/{log.pk}/").status_code == 200

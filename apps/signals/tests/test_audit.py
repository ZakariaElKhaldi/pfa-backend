import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.signals.models import DecisionLog, SignalSnapshot
from apps.tickers.models import Ticker


@pytest.fixture
def admin_user(db):
    return CustomUser.objects.create_user(
        username="admin", email="admin@example.com", password="adminpass123", role="admin"
    )


@pytest.fixture
def regular_user(db):
    return CustomUser.objects.create_user(
        username="user", email="user@example.com", password="userpass123", role="user"
    )


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    token = RefreshToken.for_user(admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.fixture
def user_client(regular_user):
    client = APIClient()
    token = RefreshToken.for_user(regular_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestDecisionAudit:
    def test_admin_can_list_decisions(self, admin_client):
        resp = admin_client.get("/api/audit/decisions/")
        assert resp.status_code == 200

    def test_regular_user_denied(self, user_client):
        resp = user_client.get("/api/audit/decisions/")
        assert resp.status_code == 403

    def test_unauthenticated_denied(self):
        client = APIClient()
        resp = client.get("/api/audit/decisions/")
        assert resp.status_code == 401

    def test_list_is_paginated_and_filterable(self, admin_client):
        ticker = Ticker.objects.create(symbol="AAPL")
        snap = SignalSnapshot.objects.create(
            ticker=ticker, sentiment=0.1, momentum=0.2, consistency=0.3,
            signal="BUY", post_count=4,
        )
        DecisionLog.objects.create(
            signal_snapshot=snap,
            ticker=ticker,
            input_summary={},
            scoring_detail={"method": "rule_based"},
            engine_output={"signal": "BUY", "method": "rule_based", "confidence": 0.8},
            alerts_triggered=[],
        )

        resp = admin_client.get("/api/audit/decisions/?ticker=AAPL&signal=BUY&method=rule_based&page=1")

        assert resp.status_code == 200
        assert resp.data["count"] == 1
        assert resp.data["results"][0]["ticker_symbol"] == "AAPL"

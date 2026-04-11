import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.strategies.models import StrategyRule


@pytest.fixture
def user(db):
    return CustomUser.objects.create_user(
        username="testuser", email="test@example.com", password="testpass123"
    )


@pytest.fixture
def other_user(db):
    return CustomUser.objects.create_user(
        username="other", email="other@example.com", password="pass123"
    )


@pytest.fixture
def ticker(db):
    from apps.tickers.models import Ticker
    return Ticker.objects.create(symbol="AAPL", name="Apple Inc.")


@pytest.fixture
def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


@pytest.mark.django_db
class TestStrategyCRUD:
    def test_create_rule(self, auth_client, user):
        resp = auth_client.post("/api/strategies/", {
            "name": "Buy on bullish sentiment",
            "conditions": [
                {"field": "sentiment_score", "operator": "gt", "value": "0.7", "logical_op": "AND", "order": 0},
                {"field": "rsi", "operator": "lt", "value": "30", "logical_op": "AND", "order": 1},
            ],
            "actions": [
                {"action_type": "notify", "config": {}, "order": 0},
            ],
        }, format="json")
        assert resp.status_code == 201
        assert resp.data["name"] == "Buy on bullish sentiment"
        assert len(resp.data["conditions"]) == 2
        assert len(resp.data["actions"]) == 1

    def test_list_rules(self, auth_client, user):
        StrategyRule.objects.create(user=user, name="Rule 1")
        resp = auth_client.get("/api/strategies/")
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_user_isolation(self, auth_client, other_user):
        StrategyRule.objects.create(user=other_user, name="Other's rule")
        resp = auth_client.get("/api/strategies/")
        assert len(resp.data) == 0

    def test_toggle_rule(self, auth_client, user):
        rule = StrategyRule.objects.create(user=user, name="Rule 1", is_active=False)
        resp = auth_client.post(f"/api/strategies/{rule.id}/toggle/")
        assert resp.status_code == 200
        rule.refresh_from_db()
        assert rule.is_active is True

    def test_delete_rule(self, auth_client, user):
        rule = StrategyRule.objects.create(user=user, name="Rule 1")
        resp = auth_client.delete(f"/api/strategies/{rule.id}/")
        assert resp.status_code == 204
        assert not StrategyRule.objects.filter(id=rule.id).exists()

    def test_unauthenticated_rejected(self):
        client = APIClient()
        resp = client.get("/api/strategies/")
        assert resp.status_code == 401

    def test_create_rule_with_ticker(self, auth_client, user, ticker):
        resp = auth_client.post("/api/strategies/", {
            "name": "Rule with ticker",
            "tickers": [ticker.id],
        }, format="json")
        assert resp.status_code == 201
        assert ticker.id in resp.data["tickers"]

    def test_patch_name_preserves_conditions(self, auth_client, user):
        # Create rule with one condition
        create_resp = auth_client.post("/api/strategies/", {
            "name": "Original",
            "conditions": [
                {"field": "sentiment_score", "operator": "gt", "value": "0.5", "logical_op": "AND", "order": 0},
            ],
        }, format="json")
        rule_id = create_resp.data["id"]
        # PATCH only the name — conditions should be untouched
        patch_resp = auth_client.patch(f"/api/strategies/{rule_id}/", {"name": "Renamed"}, format="json")
        assert patch_resp.status_code == 200
        assert patch_resp.data["name"] == "Renamed"
        assert len(patch_resp.data["conditions"]) == 1  # conditions preserved

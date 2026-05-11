import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.strategies.engine import evaluate_strategies_for_event
from apps.strategies.models import RuleAction, RuleCondition, StrategyExecution, StrategyRule


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
        RuleCondition.objects.create(rule=rule, field="signal", operator="eq", value="BUY", order=0)
        RuleAction.objects.create(rule=rule, action_type="notify", config={}, order=0)
        resp = auth_client.post(f"/api/strategies/{rule.id}/toggle/")
        assert resp.status_code == 200
        rule.refresh_from_db()
        assert rule.is_active is True

    def test_toggle_rule_honors_explicit_state(self, auth_client, user):
        rule = StrategyRule.objects.create(user=user, name="Rule 1", is_active=True)
        RuleCondition.objects.create(rule=rule, field="signal", operator="eq", value="BUY", order=0)
        RuleAction.objects.create(rule=rule, action_type="notify", config={}, order=0)
        resp = auth_client.post(f"/api/strategies/{rule.id}/toggle/", {"is_active": True}, format="json")
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
        rule = StrategyRule.objects.get(id=resp.data["id"])
        assert list(rule.tickers.values_list("id", flat=True)) == [ticker.id]

    def test_patch_rule_updates_tickers(self, auth_client, user, ticker):
        from apps.tickers.models import Ticker

        other_ticker = Ticker.objects.create(symbol="MSFT", name="Microsoft Corp.")
        rule = StrategyRule.objects.create(user=user, name="Rule with changed tickers")
        rule.tickers.set([ticker])

        resp = auth_client.patch(
            f"/api/strategies/{rule.id}/",
            {"tickers": [other_ticker.id]},
            format="json",
        )

        assert resp.status_code == 200
        assert resp.data["tickers"] == [other_ticker.id]
        rule.refresh_from_db()
        assert list(rule.tickers.values_list("id", flat=True)) == [other_ticker.id]

    def test_patch_conditions_and_actions_preserves_order(self, auth_client, user):
        rule = StrategyRule.objects.create(user=user, name="Rule with ordered children")
        RuleCondition.objects.create(rule=rule, field="rsi", operator="lt", value="30", order=0)
        RuleAction.objects.create(rule=rule, action_type="notify", config={}, order=0)

        resp = auth_client.patch(
            f"/api/strategies/{rule.id}/",
            {
                "conditions": [
                    {"field": "sentiment_score", "operator": "gt", "value": "0.7", "logical_op": "AND", "order": 1},
                    {"field": "price", "operator": "lt", "value": "100", "logical_op": "AND", "order": 0},
                ],
                "actions": [
                    {"action_type": "email", "config": {"target": "desk@example.com"}, "order": 1},
                    {"action_type": "log", "config": {}, "order": 0},
                ],
            },
            format="json",
        )

        assert resp.status_code == 200
        assert [condition["order"] for condition in resp.data["conditions"]] == [0, 1]
        assert [condition["field"] for condition in resp.data["conditions"]] == ["price", "sentiment_score"]
        assert [action["order"] for action in resp.data["actions"]] == [0, 1]
        assert [action["action_type"] for action in resp.data["actions"]] == ["log", "email"]

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

    def test_list_includes_execution_summary(self, auth_client, user):
        rule = StrategyRule.objects.create(user=user, name="Rule 1", is_active=True)
        StrategyExecution.objects.create(
            rule=rule,
            event_type="signal_generated",
            event_data={"ticker": "AAPL"},
            conditions_matched=[{"field": "signal"}],
            actions_taken=["notify:AAPL"],
            success=True,
        )

        resp = auth_client.get("/api/strategies/")

        assert resp.status_code == 200
        assert resp.data[0]["execution_count"] == 1
        assert resp.data[0]["last_execution_at"] is not None
        assert resp.data[0]["last_triggered_at"] is not None
        assert resp.data[0]["health"] == "working"

    def test_rejects_invalid_condition_operator(self, auth_client):
        resp = auth_client.post("/api/strategies/", {
            "name": "Bad Rule",
            "conditions": [
                {"field": "signal", "operator": "gt", "value": "BUY", "order": 0},
            ],
            "actions": [{"action_type": "notify", "config": {}, "order": 0}],
        }, format="json")

        assert resp.status_code == 400

    def test_rejects_auto_trade_action(self, auth_client):
        resp = auth_client.post("/api/strategies/", {
            "name": "Bad Action",
            "conditions": [
                {"field": "signal", "operator": "eq", "value": "BUY", "order": 0},
            ],
            "actions": [{"action_type": "auto_trade", "config": {}, "order": 0}],
        }, format="json")

        assert resp.status_code == 400

    def test_engine_logs_triggered_and_non_triggered_evaluations(self, user, ticker):
        matched = StrategyRule.objects.create(user=user, name="Matched", is_active=True)
        matched.tickers.set([ticker])
        RuleCondition.objects.create(rule=matched, field="signal", operator="eq", value="BUY", order=0)
        RuleAction.objects.create(rule=matched, action_type="notify", config={}, order=0)

        missed = StrategyRule.objects.create(user=user, name="Missed", is_active=True)
        missed.tickers.set([ticker])
        RuleCondition.objects.create(rule=missed, field="signal", operator="eq", value="SELL", order=0)
        RuleAction.objects.create(rule=missed, action_type="notify", config={}, order=0)

        executions = evaluate_strategies_for_event("signal_generated", {
            "ticker": ticker.symbol,
            "signal": "BUY",
            "sentiment": 0.8,
        })

        assert len(executions) == 2
        matched_execution = StrategyExecution.objects.get(rule=matched)
        missed_execution = StrategyExecution.objects.get(rule=missed)
        assert matched_execution.actions_taken
        assert missed_execution.actions_taken == []

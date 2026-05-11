from rest_framework import serializers

from apps.tickers.models import Ticker
from .engine import NUMERIC_FIELDS, recent_health
from .models import RuleAction, RuleCondition, StrategyExecution, StrategyRule

NUMERIC_OPERATORS = {"gt", "lt", "gte", "lte", "eq", "neq"}
ENUM_OPERATORS = {"eq", "neq"}
ENUM_VALUES = {
    "signal": {"BUY", "SELL", "HOLD"},
    "alert_type": {"divergence", "extreme_sentiment", "hype_fade", "pump_suspected"},
    "mood": {"bullish", "bearish", "uncertain", "euphoric", "panic"},
    "macd_signal": {"bullish", "bearish", "neutral"},
}


class RuleConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleCondition
        fields = ["id", "field", "operator", "value", "logical_op", "order"]

    def validate(self, attrs):
        field = attrs.get("field", getattr(self.instance, "field", None))
        operator = attrs.get("operator", getattr(self.instance, "operator", None))
        value = attrs.get("value", getattr(self.instance, "value", None))

        if operator in {"crosses_above", "crosses_below"}:
            raise serializers.ValidationError(
                {"operator": "Crossing operators are not available until prior-value evaluation is supported."}
            )

        if field in NUMERIC_FIELDS:
            if operator not in NUMERIC_OPERATORS:
                raise serializers.ValidationError({"operator": f"{operator} is not valid for {field}."})
            try:
                float(str(value))
            except (TypeError, ValueError):
                raise serializers.ValidationError({"value": f"{field} requires a numeric value."})

        if field in ENUM_VALUES:
            if operator not in ENUM_OPERATORS:
                raise serializers.ValidationError({"operator": f"{operator} is not valid for {field}."})
            if str(value) not in ENUM_VALUES[field]:
                allowed = ", ".join(sorted(ENUM_VALUES[field]))
                raise serializers.ValidationError({"value": f"{field} must be one of: {allowed}."})

        return attrs


class RuleActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleAction
        fields = ["id", "action_type", "config", "order"]

    def validate_action_type(self, value):
        if value == "auto_trade":
            raise serializers.ValidationError("Auto trade is disabled until explicit confirmation safeguards are implemented.")
        return value


class StrategyRuleSerializer(serializers.ModelSerializer):
    conditions = RuleConditionSerializer(many=True, required=False)
    actions = RuleActionSerializer(many=True, required=False)
    tickers = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Ticker.objects.all(), required=False
    )
    execution_count = serializers.SerializerMethodField()
    last_execution_at = serializers.SerializerMethodField()
    last_success_at = serializers.SerializerMethodField()
    last_failed_at = serializers.SerializerMethodField()
    last_triggered_at = serializers.SerializerMethodField()
    last_execution_success = serializers.SerializerMethodField()
    last_event_type = serializers.SerializerMethodField()
    health = serializers.SerializerMethodField()

    class Meta:
        model = StrategyRule
        fields = [
            "id", "name", "description", "tickers", "is_active",
            "conditions", "actions", "created_at", "updated_at",
            "execution_count", "last_execution_at", "last_success_at",
            "last_failed_at", "last_triggered_at", "last_execution_success",
            "last_event_type", "health",
        ]
        read_only_fields = [
            "id", "created_at", "updated_at", "execution_count", "last_execution_at",
            "last_success_at", "last_failed_at", "last_triggered_at",
            "last_execution_success", "last_event_type", "health",
        ]

    def get_execution_count(self, obj):
        return obj.executions.count()

    def get_last_execution_at(self, obj):
        execution = _last_execution(obj)
        return execution.triggered_at if execution else None

    def get_last_success_at(self, obj):
        execution = obj.executions.filter(success=True).order_by("-triggered_at").first()
        return execution.triggered_at if execution else None

    def get_last_failed_at(self, obj):
        execution = obj.executions.filter(success=False).order_by("-triggered_at").first()
        return execution.triggered_at if execution else None

    def get_last_triggered_at(self, obj):
        execution = (
            obj.executions
            .exclude(actions_taken=[])
            .order_by("-triggered_at")
            .first()
        )
        return execution.triggered_at if execution else None

    def get_last_execution_success(self, obj):
        execution = _last_execution(obj)
        return execution.success if execution else None

    def get_last_event_type(self, obj):
        execution = _last_execution(obj)
        return execution.event_type if execution else None

    def get_health(self, obj):
        return recent_health(_last_execution(obj), obj.is_active)

    def validate(self, attrs):
        conditions = attrs.get("conditions")
        actions = attrs.get("actions")
        is_active = attrs.get("is_active", getattr(self.instance, "is_active", False))
        if is_active and conditions is not None and len(conditions) == 0:
            raise serializers.ValidationError({"conditions": "An active strategy needs at least one condition."})
        if is_active and actions is not None and len(actions) == 0:
            raise serializers.ValidationError({"actions": "An active strategy needs at least one action."})
        return attrs

    def create(self, validated_data):
        conditions_data = validated_data.pop("conditions", [])
        actions_data = validated_data.pop("actions", [])
        tickers_data = validated_data.pop("tickers", [])
        rule = StrategyRule.objects.create(**validated_data)
        if tickers_data:
            rule.tickers.set(tickers_data)
        for cond in conditions_data:
            RuleCondition.objects.create(rule=rule, **cond)
        for action in actions_data:
            RuleAction.objects.create(rule=rule, **action)
        return rule

    def update(self, instance, validated_data):
        conditions_data = validated_data.pop("conditions", None)
        actions_data = validated_data.pop("actions", None)
        tickers_data = validated_data.pop("tickers", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tickers_data is not None:
            instance.tickers.set(tickers_data)

        if conditions_data is not None:
            instance.conditions.all().delete()
            for cond in conditions_data:
                RuleCondition.objects.create(rule=instance, **cond)

        if actions_data is not None:
            instance.actions.all().delete()
            for action in actions_data:
                RuleAction.objects.create(rule=instance, **action)

        return instance


class StrategyExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyExecution
        fields = [
            "id", "triggered_at", "event_type", "event_data",
            "conditions_matched", "actions_taken", "success",
        ]


def _last_execution(obj):
    return obj.executions.order_by("-triggered_at").first()

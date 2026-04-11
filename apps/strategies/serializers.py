from rest_framework import serializers

from apps.tickers.models import Ticker
from .models import RuleAction, RuleCondition, StrategyExecution, StrategyRule


class RuleConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleCondition
        fields = ["id", "field", "operator", "value", "logical_op", "order"]


class RuleActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleAction
        fields = ["id", "action_type", "config", "order"]


class StrategyRuleSerializer(serializers.ModelSerializer):
    conditions = RuleConditionSerializer(many=True, required=False)
    actions = RuleActionSerializer(many=True, required=False)
    tickers = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Ticker.objects.all(), required=False
    )

    class Meta:
        model = StrategyRule
        fields = [
            "id", "name", "description", "tickers", "is_active",
            "conditions", "actions", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

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

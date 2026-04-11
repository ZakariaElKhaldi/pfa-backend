from django.conf import settings
from django.db import models


class StrategyRule(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="strategies"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    tickers = models.ManyToManyField("tickers.Ticker", blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}:{self.name}"


class RuleCondition(models.Model):
    FIELD_CHOICES = [
        ("sentiment_score", "Sentiment Score"),
        ("signal", "Signal"),
        ("rsi", "RSI"),
        ("sma_20", "SMA 20"),
        ("ema_50", "EMA 50"),
        ("volume_change", "Volume Change"),
        ("bollinger_position", "Bollinger Position"),
        ("macd_signal", "MACD Signal"),
        ("alert_type", "Alert Type"),
        ("mood", "Market Mood"),
        ("price", "Price"),
    ]

    OPERATOR_CHOICES = [
        ("gt", ">"), ("lt", "<"), ("gte", ">="), ("lte", "<="),
        ("eq", "=="), ("neq", "!="), ("contains", "contains"),
        ("crosses_above", "crosses above"), ("crosses_below", "crosses below"),
    ]

    rule = models.ForeignKey(StrategyRule, on_delete=models.CASCADE, related_name="conditions")
    field = models.CharField(max_length=30, choices=FIELD_CHOICES)
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES)
    value = models.CharField(max_length=100)
    logical_op = models.CharField(
        max_length=3, choices=[("AND", "AND"), ("OR", "OR")], default="AND"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.field} {self.operator} {self.value}"


class RuleAction(models.Model):
    ACTION_CHOICES = [
        ("notify", "In-app Notification"),
        ("email", "Email"),
        ("webhook", "Webhook"),
        ("log", "Log"),
        ("auto_trade", "Auto Trade (post-MVP)"),
    ]

    rule = models.ForeignKey(StrategyRule, on_delete=models.CASCADE, related_name="actions")
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    config = models.JSONField(default=dict)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.action_type} (order={self.order})"


class StrategyExecution(models.Model):
    rule = models.ForeignKey(StrategyRule, on_delete=models.CASCADE, related_name="executions")
    triggered_at = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=30)
    event_data = models.JSONField()
    conditions_matched = models.JSONField()
    actions_taken = models.JSONField()
    success = models.BooleanField(default=True)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Execution {self.pk} for rule {self.rule_id} at {self.triggered_at}"

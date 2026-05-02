from rest_framework import serializers

from .models import BacktestRun


class BacktestRequestSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=10)
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    strategy = serializers.ChoiceField(
        choices=[c[0] for c in BacktestRun.STRATEGY_CHOICES], default="signal"
    )
    params = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        if attrs["start"] >= attrs["end"]:
            raise serializers.ValidationError({"end": "must be after start"})
        return attrs


class BacktestRunSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = BacktestRun
        fields = [
            "id",
            "ticker_symbol",
            "strategy",
            "params",
            "window_start",
            "window_end",
            "win_rate",
            "sharpe",
            "max_drawdown",
            "total_return",
            "trades",
            "equity_curve",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields

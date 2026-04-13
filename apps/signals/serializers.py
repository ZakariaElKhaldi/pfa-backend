from rest_framework import serializers

from .models import AlertFlag, DecisionLog, SignalAccuracy, SignalSnapshot


class SignalSnapshotSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = SignalSnapshot
        fields = [
            "id",
            "ticker_symbol",
            "sentiment",
            "momentum",
            "consistency",
            "signal",
            "post_count",
            "bullish_ratio",
            "normalized_index",
            "time_decay_score",
            "source_weighted_score",
            "positive_count",
            "negative_count",
            "neutral_count",
            "prediction_method",
            "prediction_confidence",
            "feature_importances",
            "created_at",
        ]


class AlertFlagSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = AlertFlag
        fields = [
            "id",
            "ticker_symbol",
            "type",
            "sentiment",
            "momentum",
            "consistency",
            "created_at",
            "resolved",
        ]


class SignalAccuracySerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="signal_snapshot.ticker.symbol", read_only=True)

    class Meta:
        model = SignalAccuracy
        fields = [
            "id", "ticker_symbol", "predicted", "actual_direction",
            "price_at_signal", "price_after_1h", "price_after_24h",
            "accuracy_1h", "accuracy_24h", "evaluated_at",
        ]


class DecisionLogSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = DecisionLog
        fields = [
            "id", "ticker_symbol", "timestamp", "input_summary",
            "scoring_detail", "engine_output", "alerts_triggered",
        ]

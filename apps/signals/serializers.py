from rest_framework import serializers

from .models import AlertFlag, SignalSnapshot


class SignalSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalSnapshot
        fields = [
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

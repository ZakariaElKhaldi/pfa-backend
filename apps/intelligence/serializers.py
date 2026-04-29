from rest_framework import serializers

from .models import ManipulationFlag, MarketMoodSnapshot, RetrainLog


class ManipulationFlagSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = ManipulationFlag
        fields = [
            "id",
            "ticker_symbol",
            "pattern_type",
            "confidence",
            "evidence",
            "detected_at",
            "reviewed",
        ]
        read_only_fields = ["id", "ticker_symbol", "pattern_type", "confidence", "evidence", "detected_at"]


class RetrainLogSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True, allow_null=True)

    class Meta:
        model = RetrainLog
        fields = [
            "id",
            "ticker_symbol",
            "trigger_reason",
            "old_accuracy",
            "new_accuracy",
            "model_version",
            "training_samples",
            "started_at",
            "completed_at",
            "status",
        ]
        read_only_fields = fields


class MarketMoodSnapshotSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = MarketMoodSnapshot
        fields = [
            "id",
            "ticker_symbol",
            "dominant_mood",
            "confidence",
            "window_start",
            "window_end",
            "created_at",
        ]
        read_only_fields = fields

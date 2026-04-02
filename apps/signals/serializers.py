from rest_framework import serializers
from .models import SignalSnapshot, AlertFlag


class SignalSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalSnapshot
        fields = ["sentiment", "momentum", "consistency", "signal", "post_count", "created_at"]


class AlertFlagSerializer(serializers.ModelSerializer):
    ticker_symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = AlertFlag
        fields = [
            "id", "ticker_symbol", "type", "sentiment", "momentum",
            "consistency", "created_at", "resolved",
        ]

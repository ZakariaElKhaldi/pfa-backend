from rest_framework import serializers

from .models import Ticker, Watchlist


class TickerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticker
        fields = ["symbol", "name", "created_at"]
        read_only_fields = ["created_at"]


class WatchlistSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="ticker.symbol", read_only=True)
    name = serializers.CharField(source="ticker.name", read_only=True)

    class Meta:
        model = Watchlist
        fields = ["symbol", "name", "added_at"]

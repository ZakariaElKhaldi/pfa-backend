from rest_framework import serializers

from .models import Portfolio, Position, Trade


class PositionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = Position
        fields = ["symbol", "quantity", "avg_price"]


class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["id", "cash", "positions", "created_at"]


class TradeSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="ticker.symbol", read_only=True)

    class Meta:
        model = Trade
        fields = ["symbol", "side", "quantity", "price", "executed_at"]

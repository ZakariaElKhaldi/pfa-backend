from django.db import models
from django.utils import timezone


class PriceSnapshot(models.Model):
    SOURCE_ALPACA_STREAM = "alpaca_stream"
    SOURCE_ALPACA_REST = "alpaca_rest"
    SOURCE_SEED = "seed"
    SOURCE_CHOICES = (
        (SOURCE_ALPACA_STREAM, "Alpaca Stream"),
        (SOURCE_ALPACA_REST, "Alpaca REST"),
        (SOURCE_SEED, "Seed Data"),
    )
    LIVE_SOURCES = (SOURCE_ALPACA_STREAM, SOURCE_ALPACA_REST)

    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=12, decimal_places=4)
    open_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    high_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    low_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    volume = models.BigIntegerField(default=0)
    timestamp = models.DateTimeField(db_index=True)
    source = models.CharField(
        max_length=32,
        choices=SOURCE_CHOICES,
        default=SOURCE_ALPACA_STREAM,
        db_index=True,
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.ticker.symbol}@{self.price}"


class TradeTick(models.Model):
    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="trade_ticks")
    price = models.DecimalField(max_digits=12, decimal_places=4)
    size = models.BigIntegerField(default=0)
    exchange = models.CharField(max_length=16, blank=True)
    trade_id = models.CharField(max_length=128, blank=True, db_index=True)
    conditions = models.JSONField(default=list, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ticker", "-timestamp"]),
            models.Index(fields=["ticker", "trade_id"]),
        ]

    def __str__(self):
        return f"{self.ticker.symbol} trade @{self.price}"


class ActiveMarketSubscription(models.Model):
    symbol = models.CharField(max_length=16, db_index=True)
    channel_name = models.CharField(max_length=255, unique=True)
    connected_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["symbol", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.symbol}:{self.channel_name}"

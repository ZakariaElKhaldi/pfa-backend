from django.db import models


class SignalSnapshot(models.Model):
    SIGNAL_BUY = "BUY"
    SIGNAL_SELL = "SELL"
    SIGNAL_HOLD = "HOLD"
    SIGNAL_CHOICES = [
        (SIGNAL_BUY, "BUY"),
        (SIGNAL_SELL, "SELL"),
        (SIGNAL_HOLD, "HOLD"),
    ]

    ticker = models.ForeignKey(
        "tickers.Ticker", on_delete=models.CASCADE, related_name="signals"
    )
    sentiment = models.FloatField()
    momentum = models.FloatField()
    consistency = models.FloatField()
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    post_count = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticker.symbol}:{self.signal}"


class AlertFlag(models.Model):
    TYPE_DIVERGENCE = "divergence"
    TYPE_EXTREME = "extreme_sentiment"
    TYPE_CHOICES = [
        (TYPE_DIVERGENCE, "Divergence"),
        (TYPE_EXTREME, "Extreme Sentiment"),
    ]

    ticker = models.ForeignKey(
        "tickers.Ticker", on_delete=models.CASCADE, related_name="alerts"
    )
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    sentiment = models.FloatField()
    momentum = models.FloatField()
    consistency = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticker.symbol}:{self.type}"

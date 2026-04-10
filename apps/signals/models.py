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

    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="signals")
    sentiment = models.FloatField()
    momentum = models.FloatField()
    consistency = models.FloatField()
    signal = models.CharField(max_length=4, choices=SIGNAL_CHOICES)
    post_count = models.IntegerField()
    # Phase 2: Advanced aggregation metrics (Papers 4 & 5)
    bullish_ratio = models.FloatField(null=True, blank=True)
    normalized_index = models.FloatField(null=True, blank=True)
    time_decay_score = models.FloatField(null=True, blank=True)
    source_weighted_score = models.FloatField(null=True, blank=True)
    positive_count = models.IntegerField(default=0)
    negative_count = models.IntegerField(default=0)
    neutral_count = models.IntegerField(default=0)
    # Phase 5: ML prediction metadata
    prediction_method = models.CharField(max_length=20, default="rule_based")
    prediction_confidence = models.FloatField(null=True, blank=True)
    feature_importances = models.JSONField(null=True, blank=True)
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

    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="alerts")
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


class SignalAccuracy(models.Model):
    signal_snapshot = models.OneToOneField(
        SignalSnapshot, on_delete=models.CASCADE, related_name="accuracy"
    )
    predicted = models.CharField(max_length=4)
    actual_direction = models.CharField(max_length=4)  # UP, DOWN, FLAT
    price_at_signal = models.DecimalField(max_digits=12, decimal_places=4)
    price_after_1h = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    price_after_24h = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    accuracy_1h = models.BooleanField(null=True)
    accuracy_24h = models.BooleanField(null=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.signal_snapshot.ticker.symbol}: {self.predicted} → {self.actual_direction}"


class DecisionLog(models.Model):
    signal_snapshot = models.OneToOneField(
        SignalSnapshot, on_delete=models.CASCADE, related_name="decision_log"
    )
    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    input_summary = models.JSONField()
    scoring_detail = models.JSONField()
    engine_output = models.JSONField()
    alerts_triggered = models.JSONField(default=list)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ticker", "-timestamp"]),
        ]

    def __str__(self):
        return f"Decision:{self.ticker.symbol}@{self.timestamp}"

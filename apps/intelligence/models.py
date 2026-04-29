from django.db import models


class MarketMoodSnapshot(models.Model):
    """Rolling sentiment embedding per ticker — captures how mood evolves over time."""

    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="mood_snapshots")
    embedding = models.JSONField()
    dominant_mood = models.CharField(max_length=20)  # bullish, bearish, uncertain, euphoric, panic
    confidence = models.FloatField()
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ManipulationFlag(models.Model):
    """Detected manipulation pattern — bot activity, pump-and-dump, coordinated campaigns."""

    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="manipulation_flags")
    pattern_type = models.CharField(max_length=30)  # bot_swarm, pump_dump, coordinated_spam
    confidence = models.FloatField()
    evidence = models.JSONField()
    detected_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-detected_at"]


class RetrainLog(models.Model):
    """Log of model retraining events triggered by accuracy drift."""

    ticker = models.ForeignKey(
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="retrain_logs",
        null=True,
        blank=True,
    )
    trigger_reason = models.CharField(max_length=100)
    old_accuracy = models.FloatField()
    new_accuracy = models.FloatField(null=True, blank=True)
    model_version = models.CharField(max_length=50, blank=True, default="")
    training_samples = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="running")  # running, success, failed

    class Meta:
        ordering = ["-started_at"]

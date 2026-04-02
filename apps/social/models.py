from django.db import models


class SocialPost(models.Model):
    SOURCE_REDDIT = "reddit"
    SOURCE_STOCKTWITS = "stocktwits"
    SOURCE_CHOICES = [(SOURCE_REDDIT, "Reddit"), (SOURCE_STOCKTWITS, "StockTwits")]

    LABEL_BULLISH = "bullish"
    LABEL_BEARISH = "bearish"
    LABEL_NEUTRAL = "neutral"
    LABEL_CHOICES = [
        (LABEL_BULLISH, "Bullish"),
        (LABEL_BEARISH, "Bearish"),
        (LABEL_NEUTRAL, "Neutral"),
    ]

    ticker = models.ForeignKey(
        "tickers.Ticker", on_delete=models.CASCADE, related_name="posts"
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=200)
    content = models.TextField()
    cleaned_text = models.TextField(blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, choices=LABEL_CHOICES, blank=True)
    posted_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source", "external_id")
        ordering = ["-posted_at"]

    def __str__(self):
        return f"{self.source}:{self.external_id}"

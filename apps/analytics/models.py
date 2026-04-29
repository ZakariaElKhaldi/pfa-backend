from django.db import models

from apps.accounts.models import CustomUser
from apps.tickers.models import Ticker


class BacktestRun(models.Model):
    STRATEGY_CHOICES = [
        ("signal", "Follow Signal"),
        ("sentiment_threshold", "Sentiment Threshold"),
    ]
    STATUS_CHOICES = [("ok", "OK"), ("error", "Error")]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="backtests")
    ticker = models.ForeignKey(Ticker, on_delete=models.CASCADE)
    strategy = models.CharField(max_length=30, choices=STRATEGY_CHOICES)
    params = models.JSONField(default=dict)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    win_rate = models.FloatField(null=True, blank=True)
    sharpe = models.FloatField(null=True, blank=True)
    max_drawdown = models.FloatField(null=True, blank=True)
    total_return = models.FloatField(null=True, blank=True)
    trades = models.JSONField(default=list)
    equity_curve = models.JSONField(default=list)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ok")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"backtest:{self.user.email}:{self.ticker.symbol}:{self.created_at:%Y%m%d}"

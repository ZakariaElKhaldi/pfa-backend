from decimal import Decimal

from django.conf import settings
from django.db import models


class Portfolio(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolio"
    )
    cash = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("100000.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Portfolio({self.user.email})"


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0)
    avg_price = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal("0"))

    class Meta:
        unique_together = ("portfolio", "ticker")

    def __str__(self):
        return f"Portfolio({self.portfolio.user.email}):{self.ticker.symbol}x{self.quantity}"


class Trade(models.Model):
    SIDE_BUY = "buy"
    SIDE_SELL = "sell"
    SIDE_CHOICES = [(SIDE_BUY, "Buy"), (SIDE_SELL, "Sell")]

    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="trades")
    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.PROTECT)
    side = models.CharField(max_length=4, choices=SIDE_CHOICES)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=4)
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.side} {self.quantity} {self.ticker.symbol}@{self.price}"

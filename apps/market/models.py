from django.db import models


class PriceSnapshot(models.Model):
    ticker = models.ForeignKey("tickers.Ticker", on_delete=models.CASCADE, related_name="prices")
    price = models.DecimalField(max_digits=12, decimal_places=4)
    open_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    high_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    low_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    volume = models.BigIntegerField(default=0)
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.ticker.symbol}@{self.price}"

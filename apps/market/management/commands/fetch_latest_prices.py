from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Fetch the latest price bar for every tracked ticker via Alpaca REST API"

    def handle(self, *args, **options):
        from decouple import config
        from alpaca.data import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestBarRequest
        from apps.tickers.models import Ticker
        from apps.market.models import PriceSnapshot

        api_key    = config("ALPACA_API_KEY",    default="")
        secret_key = config("ALPACA_SECRET_KEY", default="")

        if not api_key or not secret_key:
            self.stderr.write(self.style.ERROR("ALPACA_API_KEY / ALPACA_SECRET_KEY not set in .env"))
            return

        symbols = list(Ticker.objects.values_list("symbol", flat=True))
        if not symbols:
            self.stdout.write(self.style.WARNING("No tickers in database."))
            return

        self.stdout.write(f"Fetching latest bars for {len(symbols)} tickers...")

        client = StockHistoricalDataClient(api_key, secret_key)

        try:
            bars = client.get_stock_latest_bar(StockLatestBarRequest(symbol_or_symbols=symbols))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Alpaca API error: {e}"))
            return

        updated = 0
        skipped = 0
        for symbol, bar in bars.items():
            try:
                ticker = Ticker.objects.get(symbol=symbol)
            except Ticker.DoesNotExist:
                skipped += 1
                continue

            PriceSnapshot.objects.create(
                ticker=ticker,
                price=bar.close,
                open_price=bar.open,
                high_price=bar.high,
                low_price=bar.low,
                volume=bar.volume,
                timestamp=bar.timestamp if bar.timestamp else timezone.now(),
            )
            updated += 1
            self.stdout.write(f"  {symbol}: ${bar.close}")

        self.stdout.write(self.style.SUCCESS(f"\nDone — updated {updated} tickers, skipped {skipped}."))

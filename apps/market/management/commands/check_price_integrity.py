from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.market.models import PriceSnapshot
from apps.tickers.models import Ticker


class Command(BaseCommand):
    help = "Compare latest local live prices vs Alpaca latest bars for selected symbols."

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbol",
            action="append",
            dest="symbols",
            help="Ticker symbol to validate (can be passed multiple times). Defaults to all.",
        )
        parser.add_argument(
            "--max-drift-pct",
            type=float,
            default=0.5,
            help="Percent drift threshold for warning/failure (default: 0.5).",
        )

    def handle(self, *args, **options):
        from decouple import config
        from alpaca.data import StockHistoricalDataClient
        from alpaca.data.requests import StockLatestBarRequest

        api_key = config("ALPACA_API_KEY", default="")
        secret_key = config("ALPACA_SECRET_KEY", default="")
        if not api_key or not secret_key:
            self.stderr.write(self.style.ERROR("ALPACA_API_KEY / ALPACA_SECRET_KEY not set in .env"))
            return

        requested = options.get("symbols") or []
        if requested:
            symbols = [s.upper() for s in requested]
        else:
            symbols = list(Ticker.objects.values_list("symbol", flat=True))

        if not symbols:
            self.stdout.write(self.style.WARNING("No symbols to validate."))
            return

        client = StockHistoricalDataClient(api_key, secret_key)
        try:
            bars = client.get_stock_latest_bar(StockLatestBarRequest(symbol_or_symbols=symbols))
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Alpaca API error: {exc}"))
            return

        drift_threshold = Decimal(str(options["max_drift_pct"])) / Decimal("100")
        failures = 0

        for symbol in symbols:
            local = (
                PriceSnapshot.objects
                .filter(
                    ticker__symbol=symbol,
                    source__in=PriceSnapshot.LIVE_SOURCES,
                )
                .order_by("-timestamp")
                .first()
            )
            remote = bars.get(symbol)
            if not local or not remote:
                self.stdout.write(self.style.WARNING(f"{symbol}: missing local or Alpaca bar"))
                failures += 1
                continue

            local_price = Decimal(str(local.price))
            remote_price = Decimal(str(remote.close))
            drift = abs(local_price - remote_price) / remote_price if remote_price else Decimal("0")

            line = (
                f"{symbol}: local={local_price} ({local.timestamp.isoformat()}) "
                f"alpaca={remote_price} ({remote.timestamp.isoformat()}) "
                f"drift={(drift * Decimal('100')):.4f}%"
            )
            if drift > drift_threshold:
                self.stdout.write(self.style.ERROR(line))
                failures += 1
            else:
                self.stdout.write(self.style.SUCCESS(line))

        if failures:
            raise SystemExit(1)

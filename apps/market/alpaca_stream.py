import logging
import time

from decouple import config

from apps.market.utils import push_market_update

logger = logging.getLogger(__name__)


class AlpacaStreamManager:
    def __init__(self):
        self.api_key = config("ALPACA_API_KEY", default="")
        self.secret_key = config("ALPACA_SECRET_KEY", default="")

    def get_symbols(self) -> list[str]:
        from apps.tickers.models import Ticker
        return list(Ticker.objects.values_list("symbol", flat=True))

    def handle_bar(self, bar) -> None:
        """Called by Alpaca SDK for each price bar received."""
        from apps.tickers.models import Ticker
        from apps.market.models import PriceSnapshot

        try:
            ticker = Ticker.objects.get(symbol=bar.symbol)
        except Ticker.DoesNotExist:
            return

        try:
            PriceSnapshot.objects.create(
                ticker=ticker,
                price=bar.close,
                volume=bar.volume,
                timestamp=bar.timestamp,
            )
            push_market_update(
                bar.symbol,
                {
                    "type": "price",
                    "price": str(bar.close),
                    "volume": bar.volume,
                    "timestamp": bar.timestamp.isoformat(),
                },
            )
        except Exception as e:
            logger.error("Error storing bar for %s: %s", bar.symbol, e)

    def run(self) -> None:
        """Run the Alpaca stream with auto-reconnect."""
        from alpaca.data.live import StockDataStream

        while True:
            symbols = self.get_symbols()
            if not symbols:
                logger.info("No tickers tracked. Waiting 60s before retrying.")
                time.sleep(60)
                continue
            try:
                stream = StockDataStream(self.api_key, self.secret_key)
                stream.subscribe_bars(self.handle_bar, *symbols)
                logger.info("Alpaca stream started for: %s", symbols)
                stream.run()
            except Exception as e:
                logger.error("Alpaca stream error: %s. Reconnecting in 10s.", e)
                time.sleep(10)

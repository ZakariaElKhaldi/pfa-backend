from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Connect to Alpaca WebSocket and stream live trade ticks"

    def handle(self, *args, **options):
        from apps.market.alpaca_stream import AlpacaStreamManager

        backend = settings.CHANNEL_LAYERS["default"]["BACKEND"]
        if backend == "channels.layers.InMemoryChannelLayer":
            self.stderr.write(
                self.style.WARNING(
                    "Market WebSocket delivery is process-local with InMemoryChannelLayer. "
                    "Set REDIS_HOST for no-compromise real-time delivery from this daemon to Daphne."
                )
            )
        self.stdout.write("Starting Alpaca stream...")
        manager = AlpacaStreamManager()
        manager.run()

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Connect to Alpaca WebSocket and stream live price bars"

    def handle(self, *args, **options):
        import django
        from apps.market.alpaca_stream import AlpacaStreamManager

        self.stdout.write("Starting Alpaca stream...")
        manager = AlpacaStreamManager()
        manager.run()

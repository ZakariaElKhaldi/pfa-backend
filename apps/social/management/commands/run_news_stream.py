from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Connect to Alpaca News WebSocket and stream real-time news"

    def handle(self, *args, **options):
        from apps.social.news_stream import AlpacaNewsStreamManager

        self.stdout.write("Starting Alpaca news stream...")
        manager = AlpacaNewsStreamManager()
        manager.run()

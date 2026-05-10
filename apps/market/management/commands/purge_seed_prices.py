from django.core.management.base import BaseCommand

from apps.market.models import PriceSnapshot


class Command(BaseCommand):
    help = "Purge synthetic seeded PriceSnapshot rows (source=seed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many rows would be deleted without deleting.",
        )
        parser.add_argument(
            "--symbol",
            action="append",
            dest="symbols",
            help="Optional ticker symbol filter (can be passed multiple times).",
        )

    def handle(self, *args, **options):
        qs = PriceSnapshot.objects.filter(source=PriceSnapshot.SOURCE_SEED)

        symbols = options.get("symbols") or []
        if symbols:
            normalized = [s.upper() for s in symbols]
            qs = qs.filter(ticker__symbol__in=normalized)

        count = qs.count()
        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(f"[dry-run] Seed snapshots to delete: {count}")
            )
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} seeded snapshots."))

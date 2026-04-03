from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the Celery Beat schedule for the ingestion pipeline (runs every 5 minutes)"

    def handle(self, *args, **options):
        from django_celery_beat.models import IntervalSchedule, PeriodicTask

        schedule, _ = IntervalSchedule.objects.get_or_create(
            every=5,
            period=IntervalSchedule.MINUTES,
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="run-pipeline",
            defaults={
                "task": "pipeline.run_pipeline",
                "interval": schedule,
                "enabled": True,
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} pipeline schedule: every 5 minutes"))

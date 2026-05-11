"""Celery Beat schedule configuration tests."""

from datetime import timedelta

from django.conf import settings


def test_beat_schedule_defined():
    """Beat schedule must be declared so periodic tasks run in production."""
    schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", None)
    assert schedule is not None and len(schedule) > 0


def test_beat_schedule_runs_pipeline():
    """Pipeline fallback ingestion should not overlap normal runtime."""
    entry = settings.CELERY_BEAT_SCHEDULE["pipeline-run-every-15min"]
    assert entry["task"] == "pipeline.run_pipeline"
    assert entry["schedule"] == timedelta(minutes=15)
    assert entry["options"]["expires"] == 60


def test_beat_schedule_evaluates_accuracy_hourly():
    entry = settings.CELERY_BEAT_SCHEDULE["signals-evaluate-accuracy-hourly"]
    assert entry["task"] == "signals.evaluate_accuracy"
    assert entry["schedule"] == timedelta(hours=1)


def test_beat_schedule_computes_mood_hourly():
    entry = settings.CELERY_BEAT_SCHEDULE["mood-snapshots-hourly"]
    assert entry["task"] == "intelligence.compute_mood_snapshots"
    assert entry["schedule"] == timedelta(hours=1)

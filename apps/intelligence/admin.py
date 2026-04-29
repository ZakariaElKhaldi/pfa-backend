from django.contrib import admin

from .models import ManipulationFlag, MarketMoodSnapshot, RetrainLog


@admin.register(ManipulationFlag)
class ManipulationFlagAdmin(admin.ModelAdmin):
    list_display = ("ticker", "pattern_type", "confidence", "detected_at", "reviewed")
    list_filter = ("pattern_type", "reviewed")
    search_fields = ("ticker__symbol",)


@admin.register(MarketMoodSnapshot)
class MarketMoodSnapshotAdmin(admin.ModelAdmin):
    list_display = ("ticker", "dominant_mood", "confidence", "window_start", "window_end", "created_at")
    list_filter = ("dominant_mood",)
    search_fields = ("ticker__symbol",)


@admin.register(RetrainLog)
class RetrainLogAdmin(admin.ModelAdmin):
    list_display = ("ticker", "trigger_reason", "old_accuracy", "new_accuracy", "status", "started_at")
    list_filter = ("status", "trigger_reason")
    search_fields = ("ticker__symbol",)

from django.urls import path

from .views import (
    ManipulationFlagListView,
    ManipulationFlagReviewView,
    MoodSnapshotListView,
    RetrainLogListView,
)

urlpatterns = [
    path("flags/", ManipulationFlagListView.as_view(), name="manipulation-flag-list"),
    path("flags/<int:pk>/review/", ManipulationFlagReviewView.as_view(), name="manipulation-flag-review"),
    path("retrain-logs/", RetrainLogListView.as_view(), name="retrain-log-list"),
    path("mood/", MoodSnapshotListView.as_view(), name="mood-snapshot-list"),
]

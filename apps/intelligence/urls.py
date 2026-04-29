from django.urls import path

from .views import ManipulationFlagListView, ManipulationFlagReviewView, RetrainLogListView

urlpatterns = [
    path("flags/", ManipulationFlagListView.as_view(), name="manipulation-flag-list"),
    path("flags/<int:pk>/review/", ManipulationFlagReviewView.as_view(), name="manipulation-flag-review"),
    path("retrain-logs/", RetrainLogListView.as_view(), name="retrain-log-list"),
]

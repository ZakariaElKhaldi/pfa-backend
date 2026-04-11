from django.urls import path

from .views import (
    StrategyDetailView,
    StrategyExecutionListView,
    StrategyListCreateView,
    StrategyToggleView,
)

urlpatterns = [
    path("", StrategyListCreateView.as_view(), name="strategy-list"),
    path("<int:pk>/", StrategyDetailView.as_view(), name="strategy-detail"),
    path("<int:pk>/toggle/", StrategyToggleView.as_view(), name="strategy-toggle"),
    path("<int:pk>/executions/", StrategyExecutionListView.as_view(), name="strategy-executions"),
]

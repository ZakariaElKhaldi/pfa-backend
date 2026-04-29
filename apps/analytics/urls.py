from django.urls import path

from .views import TopMoversView

urlpatterns = [
    path("top-movers/", TopMoversView.as_view(), name="analytics-top-movers"),
]

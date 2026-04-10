from django.urls import path

from .views import TickerExportView

urlpatterns = [
    path("<str:symbol>/", TickerExportView.as_view(), name="ticker-export"),
]

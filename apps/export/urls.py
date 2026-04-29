from django.urls import path

from .views import BulkExportView, GlobalSignalExportView, PortfolioExportView, TickerExportView

urlpatterns = [
    path("signals/", GlobalSignalExportView.as_view(), name="export-signals"),
    path("portfolio/", PortfolioExportView.as_view(), name="export-portfolio"),
    path("bulk/", BulkExportView.as_view(), name="export-bulk"),
    path("<str:symbol>/", TickerExportView.as_view(), name="ticker-export"),
]

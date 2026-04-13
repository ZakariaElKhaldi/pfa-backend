from django.urls import path

from .views import GlobalSignalExportView, PortfolioExportView, TickerExportView

urlpatterns = [
    path("signals/", GlobalSignalExportView.as_view(), name="export-signals"),
    path("portfolio/", PortfolioExportView.as_view(), name="export-portfolio"),
    path("<str:symbol>/", TickerExportView.as_view(), name="ticker-export"),
]

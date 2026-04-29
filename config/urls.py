from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.tickers.urls")),
    path("api/", include("apps.social.urls")),
    path("api/", include("apps.market.urls")),
    path("api/", include("apps.signals.urls")),
    path("api/", include("apps.portfolio.urls")),
    path("api/export/", include("apps.export.urls")),
    path("api/strategies/", include("apps.strategies.urls")),
    path("api/intelligence/", include("apps.intelligence.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
]

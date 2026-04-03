from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.tickers.urls")),
    path("", include("apps.social.urls")),
    path("", include("apps.market.urls")),
    path("", include("apps.signals.urls")),
    path("", include("apps.portfolio.urls")),
]

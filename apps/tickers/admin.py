from django.contrib import admin

from .models import Ticker, Watchlist


@admin.register(Ticker)
class TickerAdmin(admin.ModelAdmin):
    list_display = ("symbol", "name", "sector", "created_at")
    search_fields = ("symbol", "name", "sector")
    list_filter = ("sector",)


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("user", "ticker", "added_at")

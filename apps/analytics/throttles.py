from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle


class AnalystExportThrottle(ScopedRateThrottle):
    scope = "analyst_export"


class BacktestThrottle(UserRateThrottle):
    scope = "backtest"

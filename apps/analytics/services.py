"""Pure functions powering analytics endpoints. No DRF imports here."""
from datetime import timedelta
from typing import Literal

from django.utils import timezone

from apps.signals.models import SignalSnapshot

WindowSpec = Literal["1h", "24h", "7d", "30d"]
WINDOW_MAP = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}


def parse_window(raw: str) -> timedelta:
    if raw not in WINDOW_MAP:
        raise ValueError(f"Invalid window: {raw!r}. Allowed: {sorted(WINDOW_MAP)}")
    return WINDOW_MAP[raw]


def compute_top_movers(window: timedelta, limit: int, direction: str = "both") -> list[dict]:
    """Largest changes in `normalized_index` per ticker over the window."""
    end = timezone.now()
    start = end - window

    earliest_per_ticker: dict[int, SignalSnapshot] = {}
    latest_per_ticker: dict[int, SignalSnapshot] = {}
    qs = (
        SignalSnapshot.objects
        .filter(created_at__range=(start, end), normalized_index__isnull=False)
        .select_related("ticker")
        .order_by("created_at")
    )
    for s in qs:
        latest_per_ticker[s.ticker_id] = s
        earliest_per_ticker.setdefault(s.ticker_id, s)

    movers = []
    for ticker_id, latest in latest_per_ticker.items():
        earliest = earliest_per_ticker[ticker_id]
        if earliest.id == latest.id:
            continue
        delta = (latest.normalized_index or 0) - (earliest.normalized_index or 0)
        if direction == "up" and delta < 0:
            continue
        if direction == "down" and delta > 0:
            continue
        movers.append({
            "ticker": latest.ticker.symbol,
            "signal": latest.signal,
            "prev_signal": earliest.signal,
            "delta": round(delta, 6),
            "normalized_index": latest.normalized_index,
        })

    movers.sort(key=lambda m: abs(m["delta"]), reverse=True)
    return movers[:limit]


def compute_sentiment_leaderboard(window: timedelta, limit: int) -> list[dict]:
    """Tickers ranked by latest bullish_ratio inside window."""
    end = timezone.now()
    start = end - window

    latest_per_ticker: dict[int, SignalSnapshot] = {}
    qs = (
        SignalSnapshot.objects
        .filter(created_at__range=(start, end), bullish_ratio__isnull=False)
        .select_related("ticker")
        .order_by("created_at")
    )
    for s in qs:
        latest_per_ticker[s.ticker_id] = s

    rows = [
        {
            "ticker": s.ticker.symbol,
            "bullish_ratio": s.bullish_ratio,
            "post_count": s.post_count,
            "sentiment_score": s.sentiment,
        }
        for s in latest_per_ticker.values()
    ]
    rows.sort(key=lambda r: r["bullish_ratio"], reverse=True)
    return rows[:limit]

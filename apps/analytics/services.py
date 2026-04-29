"""Pure functions powering analytics endpoints. No DRF imports here."""
import statistics
from datetime import timedelta
from typing import Literal

from django.utils import timezone

from apps.market.models import PriceSnapshot
from apps.signals.models import SignalSnapshot
from apps.social.models import SocialPost
from apps.tickers.models import Ticker

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


def _pearson(x: list[float], y: list[float]) -> float:
    if len(x) < 2 or len(y) < 2 or len(x) != len(y):
        return 0.0
    if statistics.pstdev(x) == 0 or statistics.pstdev(y) == 0:
        return 0.0
    n = len(x)
    mx, my = statistics.mean(x), statistics.mean(y)
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den_x = sum((xi - mx) ** 2 for xi in x) ** 0.5
    den_y = sum((yi - my) ** 2 for yi in y) ** 0.5
    if den_x == 0 or den_y == 0:
        return 0.0
    return round(num / (den_x * den_y), 6)


def compute_correlation_matrix(symbols: list[str], window: timedelta, metric: str) -> dict:
    if len(symbols) < 2:
        raise ValueError("Need at least 2 symbols for correlation")
    if len(symbols) > 10:
        raise ValueError("Maximum 10 symbols allowed")
    if metric not in ("price", "sentiment"):
        raise ValueError("metric must be 'price' or 'sentiment'")

    end = timezone.now()
    start = end - window
    series_per_symbol: dict[str, list[float]] = {}

    for symbol in symbols:
        try:
            ticker = Ticker.objects.get(symbol=symbol.upper())
        except Ticker.DoesNotExist:
            raise ValueError(f"Unknown ticker: {symbol}")
        if metric == "price":
            qs = PriceSnapshot.objects.filter(
                ticker=ticker, timestamp__range=(start, end)
            ).order_by("timestamp")
            series_per_symbol[ticker.symbol] = [float(p.price) for p in qs]
        else:
            qs = SocialPost.objects.filter(
                ticker=ticker, posted_at__range=(start, end),
                sentiment_score__isnull=False,
            ).order_by("posted_at")
            series_per_symbol[ticker.symbol] = [p.sentiment_score for p in qs]

    min_len = min((len(s) for s in series_per_symbol.values()), default=0)
    aligned = {sym: vals[-min_len:] for sym, vals in series_per_symbol.items()}

    syms = list(aligned.keys())
    matrix = [
        [_pearson(aligned[a], aligned[b]) for b in syms]
        for a in syms
    ]
    return {"symbols": syms, "matrix": matrix}


def compute_sector_rollup(window: timedelta) -> list[dict]:
    """Aggregate latest snapshot per ticker grouped by sector."""
    end = timezone.now()
    start = end - window

    latest_per_ticker: dict[int, SignalSnapshot] = {}
    qs = (
        SignalSnapshot.objects
        .filter(created_at__range=(start, end), normalized_index__isnull=False)
        .select_related("ticker")
        .order_by("created_at")
    )
    for s in qs:
        latest_per_ticker[s.ticker_id] = s

    by_sector: dict[str, list[SignalSnapshot]] = {}
    for s in latest_per_ticker.values():
        sector = s.ticker.sector or "Uncategorised"
        by_sector.setdefault(sector, []).append(s)

    rows = []
    for sector, snaps in by_sector.items():
        rows.append({
            "sector": sector,
            "ticker_count": len(snaps),
            "avg_signal": round(sum(s.normalized_index for s in snaps) / len(snaps), 6),
            "avg_sentiment": round(sum(s.sentiment for s in snaps) / len(snaps), 6),
        })
    rows.sort(key=lambda r: r["avg_signal"], reverse=True)
    return rows

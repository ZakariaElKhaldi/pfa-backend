"""Pure functions powering analytics endpoints. No DRF imports here."""
import math
import statistics
from datetime import datetime, timedelta
from typing import Literal

from django.utils import timezone

from apps.accounts.models import CustomUser
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
                ticker=ticker,
                timestamp__range=(start, end),
                source__in=PriceSnapshot.LIVE_SOURCES,
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


def compute_signal_heatmap(symbols: list[str], window: timedelta) -> dict:
    """For each ticker, list (signal_index, price_change_pct) bucketed by snapshot."""
    if not symbols:
        raise ValueError("symbols query param required")

    end = timezone.now()
    start = end - window
    rows = []
    for symbol in symbols:
        try:
            ticker = Ticker.objects.get(symbol=symbol.upper())
        except Ticker.DoesNotExist:
            raise ValueError(f"Unknown ticker: {symbol}")

        signals = list(
            SignalSnapshot.objects.filter(
                ticker=ticker, created_at__range=(start, end),
                normalized_index__isnull=False,
            ).order_by("created_at")
        )
        prices = list(
            PriceSnapshot.objects.filter(
                ticker=ticker, timestamp__range=(start, end),
                source__in=PriceSnapshot.LIVE_SOURCES,
            ).order_by("timestamp")
        )
        if not prices:
            rows.append({"ticker": ticker.symbol, "buckets": []})
            continue
        first_price = float(prices[0].price)
        buckets = []
        price_iter = iter(prices)
        next_price = next(price_iter, None)
        for snap in signals:
            while next_price and next_price.timestamp < snap.created_at:
                next_price = next(price_iter, None)
            ref_price = float(next_price.price) if next_price else float(prices[-1].price)
            buckets.append({
                "ts": snap.created_at.isoformat(),
                "signal": snap.normalized_index,
                "price_change": round((ref_price - first_price) / first_price, 6) if first_price else 0.0,
            })
        rows.append({"ticker": ticker.symbol, "buckets": buckets})
    return {"rows": rows}


def run_backtest(
    *,
    user: CustomUser,
    symbol: str,
    start: datetime,
    end: datetime,
    strategy: str,
    params: dict,
):
    """Walk-forward backtest with `strategy='signal'` only (MVP)."""
    from apps.analytics.models import BacktestRun

    if start >= end:
        raise ValueError("start must be before end")
    if (end - start) > timedelta(days=365):
        raise ValueError("window cannot exceed 365 days")
    if strategy not in ("signal", "sentiment_threshold"):
        raise ValueError(f"strategy {strategy!r} not yet implemented")

    try:
        ticker = Ticker.objects.get(symbol=symbol.upper())
    except Ticker.DoesNotExist:
        raise ValueError(f"Unknown ticker: {symbol}")

    signals = list(
        SignalSnapshot.objects
        .filter(ticker=ticker, created_at__range=(start, end))
        .order_by("created_at")
    )
    prices = list(
        PriceSnapshot.objects
        .filter(
            ticker=ticker,
            timestamp__range=(start, end),
            source__in=PriceSnapshot.LIVE_SOURCES,
        )
        .order_by("timestamp")
    )
    if not signals or not prices:
        return BacktestRun.objects.create(
            user=user, ticker=ticker, strategy=strategy, params=params,
            window_start=start, window_end=end,
            trades=[], equity_curve=[],
            win_rate=0.0, sharpe=0.0, max_drawdown=0.0, total_return=0.0,
            status="ok",
        )

    starting_cash = 10_000.0
    cash = starting_cash
    shares = 0.0
    trades: list[dict] = []
    equity_curve: list[dict] = []
    pos_open_price: float | None = None

    price_idx = 0
    for snap in signals:
        while price_idx < len(prices) - 1 and prices[price_idx].timestamp < snap.created_at:
            price_idx += 1
        price_now = float(prices[price_idx].price)
        bullish_ratio = snap.bullish_ratio or 0.0

        if strategy == "signal":
            buy_condition = (snap.signal == "BUY")
            sell_condition = (snap.signal in ("SELL", "HOLD"))
        elif strategy == "sentiment_threshold":
            threshold = float(params.get("threshold", 0.6))
            lower_bound = 1.0 - threshold
            buy_condition = (bullish_ratio >= threshold)
            sell_condition = (bullish_ratio <= lower_bound)
        else:
            buy_condition = sell_condition = False

        if buy_condition and shares == 0:
            shares = cash / price_now
            cash = 0
            pos_open_price = price_now
            trades.append({
                "ts": snap.created_at.isoformat(), "side": "buy",
                "price": price_now, "signal": snap.signal,
            })
        elif sell_condition and shares > 0:
            cash = shares * price_now
            trades.append({
                "ts": snap.created_at.isoformat(), "side": "sell",
                "price": price_now, "signal": snap.signal,
                "pnl": (price_now - pos_open_price) / pos_open_price if pos_open_price else 0.0,
            })
            shares = 0
            pos_open_price = None

        equity = cash + shares * price_now
        equity_curve.append({"ts": snap.created_at.isoformat(), "equity": round(equity, 4)})

    final_equity = cash + shares * float(prices[-1].price)
    total_return = (final_equity - starting_cash) / starting_cash

    closed_trades = [t for t in trades if t["side"] == "sell"]
    wins = [t for t in closed_trades if t.get("pnl", 0) > 0]
    win_rate = (len(wins) / len(closed_trades)) if closed_trades else 0.0

    if len(equity_curve) > 1:
        rets = [
            (equity_curve[i]["equity"] - equity_curve[i - 1]["equity"]) / equity_curve[i - 1]["equity"]
            for i in range(1, len(equity_curve))
            if equity_curve[i - 1]["equity"]
        ]
        mean_r = sum(rets) / len(rets) if rets else 0.0
        var = sum((r - mean_r) ** 2 for r in rets) / len(rets) if rets else 0.0
        std_r = math.sqrt(var)
        sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    peak = -math.inf
    max_dd = 0.0
    for point in equity_curve:
        peak = max(peak, point["equity"])
        if peak > 0:
            dd = (point["equity"] - peak) / peak
            max_dd = min(max_dd, dd)

    return BacktestRun.objects.create(
        user=user, ticker=ticker, strategy=strategy, params=params,
        window_start=start, window_end=end,
        trades=trades, equity_curve=equity_curve,
        win_rate=round(win_rate, 6),
        sharpe=round(sharpe, 6),
        max_drawdown=round(max_dd, 6),
        total_return=round(total_return, 6),
        status="ok",
    )

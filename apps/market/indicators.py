"""
Technical indicators for market data analysis.
Pure functions operating on lists of floats. No Django ORM dependency.
Based on Papers 1 & 6: combine technical indicators with sentiment features.
"""

import math


def sma(prices: list[float], period: int) -> float | None:
    """Simple Moving Average over the last `period` prices."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def ema(prices: list[float], period: int) -> float | None:
    """Exponential Moving Average over the last `period` prices."""
    if len(prices) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema_val = sum(prices[:period]) / period  # seed with SMA
    for price in prices[period:]:
        ema_val = (price - ema_val) * multiplier + ema_val
    return ema_val


def rsi(prices: list[float], period: int = 14) -> float | None:
    """Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]

    gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    for d in deltas[period:]:
        avg_gain = (avg_gain * (period - 1) + max(d, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0.0)) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def bollinger_bands(
    prices: list[float], period: int = 20, num_std: float = 2.0
) -> dict | None:
    """Returns {upper, middle, lower} Bollinger Bands."""
    if len(prices) < period:
        return None
    window = prices[-period:]
    middle = sum(window) / period
    variance = sum((p - middle) ** 2 for p in window) / period
    std = math.sqrt(variance)
    return {
        "upper": middle + num_std * std,
        "middle": middle,
        "lower": middle - num_std * std,
    }


def macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal_period: int = 9
) -> dict | None:
    """Returns {macd, signal, histogram}."""
    if len(prices) < slow + signal_period:
        return None
    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)
    if fast_ema is None or slow_ema is None:
        return None
    macd_line = fast_ema - slow_ema

    # Build MACD series for signal line
    macd_series = []
    for i in range(slow, len(prices) + 1):
        f = ema(prices[:i], fast)
        s = ema(prices[:i], slow)
        if f is not None and s is not None:
            macd_series.append(f - s)

    if len(macd_series) < signal_period:
        return None

    signal_line = ema(macd_series, signal_period)
    if signal_line is None:
        return None

    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    }


def historical_volatility(prices: list[float], period: int = 20) -> float | None:
    """Annualized historical volatility based on log returns."""
    if len(prices) < period + 1:
        return None
    window = prices[-(period + 1):]
    log_returns = [math.log(window[i + 1] / window[i]) for i in range(len(window) - 1) if window[i] > 0]
    if not log_returns:
        return None
    mean_return = sum(log_returns) / len(log_returns)
    variance = sum((r - mean_return) ** 2 for r in log_returns) / len(log_returns)
    return math.sqrt(variance)


def average_true_range(
    highs: list[float], lows: list[float], closes: list[float], period: int = 14
) -> float | None:
    """Average True Range (ATR)."""
    n = min(len(highs), len(lows), len(closes))
    if n < period + 1:
        return None

    true_ranges = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    atr = sum(true_ranges[:period]) / period
    for tr in true_ranges[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr

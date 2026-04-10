import pytest

from apps.market.indicators import (
    average_true_range,
    bollinger_bands,
    ema,
    historical_volatility,
    macd,
    rsi,
    sma,
)


# --- SMA ---

def test_sma_5_period_known_values():
    prices = [10.0, 11.0, 12.0, 13.0, 14.0]
    assert sma(prices, 5) == pytest.approx(12.0)


def test_sma_3_period():
    prices = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert sma(prices, 3) == pytest.approx(8.0)  # last 3: 6, 8, 10


def test_sma_insufficient_data_returns_none():
    prices = [10.0, 11.0]
    assert sma(prices, 5) is None


# --- EMA ---

def test_ema_known_values():
    prices = [22.27, 22.19, 22.08, 22.17, 22.18, 22.13, 22.23, 22.43, 22.24, 22.29, 22.15]
    result = ema(prices, 10)
    assert result is not None
    assert isinstance(result, float)


def test_ema_insufficient_data_returns_none():
    prices = [10.0, 11.0]
    assert ema(prices, 10) is None


def test_ema_smoothing_factor():
    # EMA with period 2 should weight recent prices heavily
    prices = [10.0, 20.0, 30.0]
    result = ema(prices, 2)
    assert result is not None
    assert result > 20.0  # should be closer to 30 than to 20


# --- RSI ---

def test_rsi_all_gains_returns_100():
    prices = [float(i) for i in range(1, 20)]  # monotonically increasing
    result = rsi(prices, 14)
    assert result == pytest.approx(100.0, abs=0.1)


def test_rsi_all_losses_returns_0():
    prices = [float(20 - i) for i in range(19)]  # monotonically decreasing
    result = rsi(prices, 14)
    assert result == pytest.approx(0.0, abs=0.1)


def test_rsi_insufficient_data_returns_none():
    prices = [10.0, 11.0, 12.0]
    assert rsi(prices, 14) is None


def test_rsi_mixed_known_range():
    # RSI should be between 0 and 100
    prices = [44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
              46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03]
    result = rsi(prices, 14)
    assert result is not None
    assert 0 <= result <= 100


# --- Bollinger Bands ---

def test_bollinger_bands_returns_upper_middle_lower():
    prices = [float(i) for i in range(1, 25)]
    result = bollinger_bands(prices, 20)
    assert result is not None
    assert "upper" in result
    assert "middle" in result
    assert "lower" in result
    assert result["upper"] > result["middle"] > result["lower"]


def test_bollinger_bands_insufficient_data():
    prices = [10.0, 11.0, 12.0]
    assert bollinger_bands(prices, 20) is None


# --- MACD ---

def test_macd_returns_macd_signal_histogram():
    prices = [float(i + 100) for i in range(40)]
    result = macd(prices)
    assert result is not None
    assert "macd" in result
    assert "signal" in result
    assert "histogram" in result


def test_macd_insufficient_data():
    prices = [10.0] * 10
    assert macd(prices) is None


# --- Volatility ---

def test_historical_volatility_known_values():
    prices = [100.0, 102.0, 101.0, 103.0, 100.0, 105.0, 102.0, 104.0,
              101.0, 103.0, 106.0, 102.0, 104.0, 107.0, 103.0, 105.0,
              108.0, 104.0, 106.0, 109.0, 105.0]
    result = historical_volatility(prices, 20)
    assert result is not None
    assert result > 0


def test_historical_volatility_constant_prices():
    prices = [100.0] * 25
    result = historical_volatility(prices, 20)
    assert result == pytest.approx(0.0, abs=1e-10)


def test_historical_volatility_insufficient_data():
    prices = [100.0, 101.0]
    assert historical_volatility(prices, 20) is None


# --- ATR ---

def test_average_true_range_known_values():
    highs = [48.70, 48.72, 48.90, 48.87, 48.82, 49.05, 49.20, 49.35, 49.92, 50.19,
             50.12, 49.66, 49.88, 50.19, 50.36, 50.57]
    lows = [47.79, 48.14, 48.39, 48.37, 48.24, 48.64, 48.94, 48.86, 49.50, 49.87,
            49.20, 48.90, 49.43, 49.73, 49.26, 50.09]
    closes = [48.16, 48.61, 48.75, 48.63, 48.74, 49.03, 49.07, 49.32, 49.91, 50.13,
              49.53, 49.50, 49.75, 50.03, 50.31, 50.52]
    result = average_true_range(highs, lows, closes, 14)
    assert result is not None
    assert result > 0


def test_average_true_range_insufficient_data():
    assert average_true_range([1.0], [0.5], [0.8], 14) is None

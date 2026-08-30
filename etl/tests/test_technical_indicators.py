from __future__ import annotations

import numpy as np
import pandas as pd

from transform.indicators import compute_indicators


def _make_candles(ticker: str, n: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prices = 100 + np.cumsum(rng.normal(0.5, 1.0, n))
    return pd.DataFrame(
        {
            "ticker": [ticker] * n,
            "bucket_start": pd.date_range("2026-08-30 09:00", periods=n, freq="1min"),
            "open": prices,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices,
            "volume": [100] * n,
            "tick_count": [2] * n,
        }
    )


def test_rsi_within_valid_range():
    candles = _make_candles("BBCA", 25)

    result = compute_indicators(candles, "1m", sma_period=5, ema_period=5, rsi_period=5, bollinger_period=5)

    assert result["rsi"].dropna().between(0, 100).all()


def test_bollinger_bands_ordered_correctly():
    candles = _make_candles("BBCA", 25)

    result = compute_indicators(candles, "1m", bollinger_period=5)
    valid = result.dropna(subset=["bollinger_upper", "bollinger_middle", "bollinger_lower"])

    assert (valid["bollinger_upper"] >= valid["bollinger_middle"]).all()
    assert (valid["bollinger_middle"] >= valid["bollinger_lower"]).all()


def test_multi_ticker_no_cross_contamination():
    bbca = _make_candles("BBCA", 25, seed=1)
    tlkm = _make_candles("TLKM", 25, seed=1)
    tlkm["close"] = tlkm["close"] + 1000
    combined = pd.concat([bbca, tlkm], ignore_index=True)

    result = compute_indicators(combined, "1m", sma_period=5)

    bbca_sma = result[result["ticker"] == "BBCA"]["sma"].dropna().iloc[-1]
    tlkm_sma = result[result["ticker"] == "TLKM"]["sma"].dropna().iloc[-1]
    assert tlkm_sma - bbca_sma > 900


def test_early_rows_are_nan_before_window_fills():
    candles = _make_candles("BBCA", 10)

    result = compute_indicators(candles, "1m", sma_period=5)

    assert result["sma"].head(4).isna().all()
    assert result["sma"].iloc[4:].notna().all()


def test_empty_input_returns_empty_df():
    columns = ["ticker", "bucket_start", "open", "high", "low", "close", "volume", "tick_count"]
    result = compute_indicators(pd.DataFrame(columns=columns), "1m")

    assert result.empty
    assert list(result.columns) == [
        "ticker",
        "interval",
        "timestamp",
        "sma",
        "ema",
        "rsi",
        "bollinger_upper",
        "bollinger_middle",
        "bollinger_lower",
    ]

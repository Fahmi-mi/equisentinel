from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from etl.transform.cleaning import fill_gaps, remove_outliers


def _make_candles(timestamps: list[str], close: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA"] * len(timestamps),
            "bucket_start": pd.to_datetime(timestamps),
            "open": [close] * len(timestamps),
            "high": [close + 1] * len(timestamps),
            "low": [close - 1] * len(timestamps),
            "close": [close] * len(timestamps),
            "volume": [100] * len(timestamps),
            "tick_count": [2] * len(timestamps),
        }
    )


def test_fill_gaps_inserts_missing_buckets_with_forward_fill():
    candles = _make_candles(
        ["2026-08-30 09:00", "2026-08-30 09:01", "2026-08-30 09:04"],
        close=100.0,
    )

    result = fill_gaps(candles, "1m")

    assert len(result) == 5
    assert list(result["bucket_start"]) == list(
        pd.date_range("2026-08-30 09:00", periods=5, freq="1min")
    )
    filled = result[result["bucket_start"] == pd.Timestamp("2026-08-30 09:02")].iloc[0]
    assert filled["close"] == 100.0
    assert filled["volume"] == 0
    assert filled["tick_count"] == 0


def test_fill_gaps_empty_input_returns_unchanged():
    candles = pd.DataFrame(columns=["ticker", "bucket_start", "open", "high", "low", "close", "volume", "tick_count"])

    result = fill_gaps(candles, "1m")

    assert result.empty


def test_fill_gaps_invalid_interval_raises():
    candles = _make_candles(["2026-08-30 09:00"])

    with pytest.raises(ValueError):
        fill_gaps(candles, "3m")


def test_remove_outliers_drops_extreme_returns():
    rng = np.random.default_rng(1)
    n = 30
    prices = 100 + np.cumsum(rng.normal(0, 0.5, n))
    prices[15] = prices[14] * 3

    candles = pd.DataFrame(
        {
            "ticker": ["BBCA"] * n,
            "bucket_start": pd.date_range("2026-08-30 09:00", periods=n, freq="1min"),
            "open": prices,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices,
            "volume": [10] * n,
            "tick_count": [1] * n,
        }
    )

    result = remove_outliers(candles)

    assert len(result) < n
    assert result["close"].iloc[14] * 3 not in set(result["close"])


def test_remove_outliers_stable_prices_unchanged():
    candles = _make_candles(
        [f"2026-08-30 09:{i:02d}" for i in range(10)],
    )

    result = remove_outliers(candles)

    assert len(result) == 10

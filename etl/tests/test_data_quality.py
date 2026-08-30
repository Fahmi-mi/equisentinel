from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from transform.cleaning import detect_gaps, detect_ohlc_anomalies, detect_price_outliers


def test_detect_ohlc_anomalies_flags_invalid_row():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBCA"],
            "bucket_start": pd.to_datetime(["2026-08-30 09:00", "2026-08-30 09:01"]),
            "open": [100, 100],
            "high": [105, 90],
            "low": [99, 95],
            "close": [102, 92],
            "volume": [10, 10],
            "tick_count": [1, 1],
        }
    )

    anomalies = detect_ohlc_anomalies(df)

    assert len(anomalies) == 1
    assert anomalies.iloc[0]["bucket_start"] == pd.Timestamp("2026-08-30 09:01")


def test_detect_ohlc_anomalies_flags_negative_volume():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "bucket_start": pd.to_datetime(["2026-08-30 09:00"]),
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [101],
            "volume": [-5],
            "tick_count": [1],
        }
    )

    anomalies = detect_ohlc_anomalies(df)

    assert len(anomalies) == 1


def test_detect_ohlc_anomalies_clean_data_returns_empty():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA", "BBCA"],
            "bucket_start": pd.to_datetime(["2026-08-30 09:00", "2026-08-30 09:01"]),
            "open": [100, 101],
            "high": [105, 106],
            "low": [99, 100],
            "close": [102, 103],
            "volume": [10, 20],
            "tick_count": [1, 1],
        }
    )

    anomalies = detect_ohlc_anomalies(df)

    assert anomalies.empty


def test_detect_price_outliers_flags_extreme_return():
    rng = np.random.default_rng(1)
    n = 30
    prices = 100 + np.cumsum(rng.normal(0, 0.5, n))
    prices[15] = prices[14] * 3

    df = pd.DataFrame(
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

    outliers = detect_price_outliers(df)

    assert len(outliers) >= 1


def test_detect_price_outliers_stable_prices_returns_empty():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"] * 10,
            "bucket_start": pd.date_range("2026-08-30 09:00", periods=10, freq="1min"),
            "open": [100] * 10,
            "high": [101] * 10,
            "low": [99] * 10,
            "close": [100] * 10,
            "volume": [10] * 10,
            "tick_count": [1] * 10,
        }
    )

    outliers = detect_price_outliers(df)

    assert outliers.empty


def test_detect_gaps_finds_missing_buckets():
    timestamps = pd.date_range("2026-08-30 09:00", periods=10, freq="1min").delete([4, 5])
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"] * 8,
            "bucket_start": timestamps,
            "open": [100] * 8,
            "high": [101] * 8,
            "low": [99] * 8,
            "close": [100] * 8,
            "volume": [10] * 8,
            "tick_count": [1] * 8,
        }
    )

    gaps = detect_gaps(df, "1m")

    assert len(gaps) == 2


def test_detect_gaps_no_gap_returns_empty():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"] * 5,
            "bucket_start": pd.date_range("2026-08-30 09:00", periods=5, freq="1min"),
            "open": [100] * 5,
            "high": [101] * 5,
            "low": [99] * 5,
            "close": [100] * 5,
            "volume": [10] * 5,
            "tick_count": [1] * 5,
        }
    )

    gaps = detect_gaps(df, "1m")

    assert gaps.empty


def test_detect_gaps_invalid_interval_raises():
    df = pd.DataFrame(columns=["ticker", "bucket_start", "open", "high", "low", "close", "volume", "tick_count"])

    with pytest.raises(ValueError):
        detect_gaps(df, "3m")

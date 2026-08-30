from __future__ import annotations

import pandas as pd
import pytest

from etl.transform.candles import aggregate_candles


def test_aggregates_ticks_into_bucket():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"] * 4,
            "open": [100, 101, 102, 103],
            "high": [105, 106, 107, 108],
            "low": [99, 100, 101, 102],
            "close": [101, 102, 103, 104],
            "volume": [10, 20, 30, 40],
            "timestamp": pd.to_datetime(
                [
                    "2026-08-30 09:00:05",
                    "2026-08-30 09:00:35",
                    "2026-08-30 09:01:05",
                    "2026-08-30 09:01:35",
                ]
            ),
        }
    )

    result = aggregate_candles(df, "1m")

    assert len(result) == 2
    first = result.iloc[0]
    assert first["open"] == 100
    assert first["close"] == 102
    assert first["high"] == 106
    assert first["low"] == 99
    assert first["volume"] == 30
    assert first["tick_count"] == 2


def test_multi_ticker_not_mixed():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA", "TLKM"],
            "open": [100, 3000],
            "high": [105, 3050],
            "low": [99, 2990],
            "close": [101, 3010],
            "volume": [10, 5],
            "timestamp": pd.to_datetime(["2026-08-30 09:00:05", "2026-08-30 09:00:10"]),
        }
    )

    result = aggregate_candles(df, "1m")

    assert set(result["ticker"]) == {"BBCA", "TLKM"}
    assert len(result) == 2


def test_empty_input_returns_empty_df():
    columns = ["ticker", "open", "high", "low", "close", "volume", "timestamp"]
    result = aggregate_candles(pd.DataFrame(columns=columns), "1m")

    assert result.empty
    assert list(result.columns) == ["ticker", "bucket_start", "open", "high", "low", "close", "volume", "tick_count"]


def test_invalid_interval_raises():
    df = pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "open": [100],
            "high": [105],
            "low": [99],
            "close": [101],
            "volume": [10],
            "timestamp": pd.to_datetime(["2026-08-30 09:00:05"]),
        }
    )

    with pytest.raises(ValueError):
        aggregate_candles(df, "3m")

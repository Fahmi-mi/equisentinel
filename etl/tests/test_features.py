from __future__ import annotations

import pandas as pd

from etl.transform.features import FEATURE_COLUMNS, INDICATOR_FIELDS, build_features


def _make_latest_candles() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "bucket_start": pd.to_datetime(["2026-08-30 09:59"]),
            "open": [100.0],
            "high": [102.0],
            "low": [99.0],
            "close": [101.5],
            "volume": [500],
            "tick_count": [3],
        }
    )


def _make_indicators(interval: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ticker": ["BBCA"],
            "interval": [interval],
            "timestamp": pd.to_datetime(["2026-08-30 09:59"]),
            "sma": [100.2],
            "ema": [100.4],
            "rsi": [61.0],
            "bollinger_upper": [105.0],
            "bollinger_middle": [100.5],
            "bollinger_lower": [96.0],
        }
    )


def test_build_features_merges_close_volume_and_interval_prefixed_indicators():
    result = build_features(
        _make_latest_candles(),
        {"1m": _make_indicators("1m"), "5m": _make_indicators("5m")},
    )

    assert len(result) == 1
    row = result.iloc[0]
    assert row["ticker"] == "BBCA"
    assert row["timestamp"] == pd.Timestamp("2026-08-30 09:59")

    features = row["features"]
    assert features["close"] == 101.5
    assert features["volume"] == 500
    for field in INDICATOR_FIELDS:
        assert f"1m_{field}" in features
        assert f"5m_{field}" in features


def test_build_features_skips_empty_or_nan_indicators():
    candles = _make_latest_candles()
    indicators = _make_indicators("1m")
    indicators["rsi"] = None  # NaN → tidak dimasukkan

    result = build_features(candles, {"1m": indicators, "5m": pd.DataFrame()})

    features = result.iloc[0]["features"]
    assert "1m_rsi" not in features
    assert "5m_sma" not in features
    assert "1m_sma" in features


def test_build_features_empty_candles_returns_empty_df():
    result = build_features(pd.DataFrame(), {"1m": _make_indicators("1m")})

    assert result.empty
    assert list(result.columns) == FEATURE_COLUMNS

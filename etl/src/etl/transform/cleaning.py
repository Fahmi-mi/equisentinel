from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()

DEFAULT_Z_THRESHOLD = 4.0


def detect_ohlc_anomalies(candles: pd.DataFrame) -> pd.DataFrame:
    invalid = candles[
        (candles["high"] < candles["low"])
        | (candles["high"] < candles["open"])
        | (candles["high"] < candles["close"])
        | (candles["low"] > candles["open"])
        | (candles["low"] > candles["close"])
        | (candles["volume"] < 0)
    ]
    return invalid


def detect_price_outliers(candles: pd.DataFrame, z_threshold: float = DEFAULT_Z_THRESHOLD) -> pd.DataFrame:
    flagged: list[pd.DataFrame] = []

    for ticker, group in candles.groupby("ticker"):
        group = group.sort_values("bucket_start")
        returns = group["close"].pct_change()
        std = returns.std()
        if std == 0 or pd.isna(std):
            continue

        z_scores = (returns - returns.mean()) / std
        flagged.append(group[z_scores.abs() > z_threshold])

    if not flagged:
        return candles.iloc[0:0]

    return pd.concat(flagged, ignore_index=True)


def detect_gaps(candles: pd.DataFrame, interval: str) -> pd.DataFrame:
    freq_map = {"1m": "1min", "5m": "5min", "1h": "1h"}
    if interval not in freq_map:
        raise ValueError(f"unsupported interval: {interval}")

    freq = freq_map[interval]
    gap_rows: list[dict] = []

    for ticker, group in candles.groupby("ticker"):
        group = group.sort_values("bucket_start")
        if len(group) < 2:
            continue

        expected = pd.date_range(group["bucket_start"].min(), group["bucket_start"].max(), freq=freq)
        missing = expected.difference(pd.DatetimeIndex(group["bucket_start"]))
        gap_rows.extend({"ticker": ticker, "bucket_start": ts} for ts in missing)

    return pd.DataFrame(gap_rows, columns=["ticker", "bucket_start"])


CANDLE_FREQ_MAP = {"1m": "1min", "5m": "5min", "1h": "1h"}

PRICE_COLUMNS = ["open", "high", "low", "close"]


def fill_gaps(candles: pd.DataFrame, interval: str) -> pd.DataFrame:
    if interval not in CANDLE_FREQ_MAP:
        raise ValueError(f"unsupported interval: {interval}")
    if candles.empty:
        return candles

    freq = CANDLE_FREQ_MAP[interval]
    filled: list[pd.DataFrame] = []

    for ticker, group in candles.groupby("ticker"):
        group = group.sort_values("bucket_start").set_index("bucket_start")
        full_index = pd.date_range(group.index.min(), group.index.max(), freq=freq)
        full_index.name = "bucket_start"
        group = group.reindex(full_index)
        group[PRICE_COLUMNS] = group[PRICE_COLUMNS].ffill()
        group["volume"] = group["volume"].fillna(0).astype("int64")
        group["tick_count"] = group["tick_count"].fillna(0).astype("int64")
        group = group.reset_index()
        group["ticker"] = ticker
        filled.append(group)

    return pd.concat(filled, ignore_index=True)


def remove_outliers(candles: pd.DataFrame, z_threshold: float = DEFAULT_Z_THRESHOLD) -> pd.DataFrame:
    flagged = detect_price_outliers(candles, z_threshold)
    if flagged.empty:
        return candles
    return candles.drop(flagged.index)

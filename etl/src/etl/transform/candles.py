from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()

INTERVAL_TO_PANDAS_FREQ = {
    "1m": "1min",
    "5m": "5min",
    "1h": "1h",
}

CANDLE_COLUMNS = ["ticker", "bucket_start", "open", "high", "low", "close", "volume", "tick_count"]


def aggregate_candles(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if interval not in INTERVAL_TO_PANDAS_FREQ:
        raise ValueError(f"unsupported interval: {interval}")

    if df.empty:
        return pd.DataFrame(columns=CANDLE_COLUMNS)

    freq = INTERVAL_TO_PANDAS_FREQ[interval]
    ticked = df.sort_values("timestamp").set_index("timestamp")

    grouped = ticked.groupby(["ticker", pd.Grouper(freq=freq)])
    candles = grouped.agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        tick_count=("close", "count"),
    )
    candles = candles.reset_index().rename(columns={"timestamp": "bucket_start"})

    log.info("aggregate_candles_done", interval=interval, row_count=len(candles))
    return candles[CANDLE_COLUMNS]

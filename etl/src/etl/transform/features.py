from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()

FEATURE_COLUMNS = ["ticker", "timestamp", "features"]

INDICATOR_FIELDS = [
    "sma",
    "ema",
    "rsi",
    "bollinger_upper",
    "bollinger_middle",
    "bollinger_lower",
]


def build_features(
    latest_candles: pd.DataFrame,
    indicators_by_interval: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    if latest_candles.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    rows: list[dict[str, object]] = []
    for ticker, candle_group in latest_candles.groupby("ticker"):
        candle = candle_group.sort_values("bucket_start").iloc[-1]
        features: dict[str, object] = {
            "close": float(candle["close"]),
            "volume": int(candle["volume"]),
        }

        for interval, indicators in indicators_by_interval.items():
            if indicators.empty:
                continue
            ticker_rows = indicators.loc[indicators["ticker"] == ticker].sort_values("timestamp")
            if ticker_rows.empty:
                continue
            latest = ticker_rows.iloc[-1]
            for field in INDICATOR_FIELDS:
                value = latest.get(field)
                if pd.notna(value):
                    features[f"{interval}_{field}"] = float(value)

        rows.append(
            {
                "ticker": ticker,
                "timestamp": candle["bucket_start"],
                "features": features,
            }
        )

    result = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    log.info("build_features_done", row_count=len(result))
    return result

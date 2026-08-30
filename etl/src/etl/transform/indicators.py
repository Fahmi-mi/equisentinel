from __future__ import annotations

import pandas as pd
import structlog

log = structlog.get_logger()

INDICATOR_COLUMNS = [
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

DEFAULT_SMA_PERIOD = 20
DEFAULT_EMA_PERIOD = 20
DEFAULT_RSI_PERIOD = 14
DEFAULT_BOLLINGER_PERIOD = 20
DEFAULT_BOLLINGER_STD = 2.0


def compute_indicators(
    candles: pd.DataFrame,
    interval: str,
    sma_period: int = DEFAULT_SMA_PERIOD,
    ema_period: int = DEFAULT_EMA_PERIOD,
    rsi_period: int = DEFAULT_RSI_PERIOD,
    bollinger_period: int = DEFAULT_BOLLINGER_PERIOD,
    bollinger_std: float = DEFAULT_BOLLINGER_STD,
) -> pd.DataFrame:
    if candles.empty:
        return pd.DataFrame(columns=INDICATOR_COLUMNS)

    candles = candles.sort_values(["ticker", "bucket_start"])
    results: list[pd.DataFrame] = []

    for ticker, group in candles.groupby("ticker"):
        close = group["close"]

        sma = close.rolling(sma_period).mean()
        ema = close.ewm(span=ema_period, adjust=False).mean()

        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(rsi_period).mean()
        avg_loss = loss.rolling(rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.where(avg_loss != 0, 100.0)

        bollinger_middle = close.rolling(bollinger_period).mean()
        std = close.rolling(bollinger_period).std()
        bollinger_upper = bollinger_middle + bollinger_std * std
        bollinger_lower = bollinger_middle - bollinger_std * std

        results.append(
            pd.DataFrame(
                {
                    "ticker": ticker,
                    "interval": interval,
                    "timestamp": group["bucket_start"],
                    "sma": sma,
                    "ema": ema,
                    "rsi": rsi,
                    "bollinger_upper": bollinger_upper,
                    "bollinger_middle": bollinger_middle,
                    "bollinger_lower": bollinger_lower,
                }
            )
        )

    indicators = pd.concat(results, ignore_index=True)
    log.info("compute_indicators_done", interval=interval, row_count=len(indicators))
    return indicators[INDICATOR_COLUMNS]

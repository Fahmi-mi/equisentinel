from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import structlog
from sqlalchemy import text

from etl.storage.warehouse_db import WarehouseDB

log = structlog.get_logger()

CANDLE_TABLES = {
    "1m": "candles_1m",
    "5m": "candles_5m",
    "1h": "candles_1h",
}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df.astype(object).where(pd.notnull(df), None)


def read_candles(db: WarehouseDB, ticker: str, interval: str, start: datetime, end: datetime) -> pd.DataFrame:
    if interval not in CANDLE_TABLES:
        raise ValueError(f"unsupported interval: {interval}")

    table = CANDLE_TABLES[interval]
    query = f"""
        SELECT ticker, bucket_start, open, high, low, close, volume, tick_count
        FROM {table}
        WHERE ticker = %(ticker)s
          AND bucket_start >= %(start)s
          AND bucket_start < %(end)s
        ORDER BY bucket_start ASC
    """

    try:
        with db.warehouse_connection() as conn:
            df = pd.read_sql(query, conn, params={"ticker": ticker, "start": start, "end": end})
    except Exception:
        log.error("read_candles_failed", ticker=ticker, interval=interval, table=table, exc_info=True)
        raise

    log.info("read_candles_done", ticker=ticker, interval=interval, row_count=len(df))
    return df


def read_technical_indicators(
    db: WarehouseDB, ticker: str, interval: str, start: datetime, end: datetime
) -> pd.DataFrame:
    query = """
        SELECT ticker, "interval", "timestamp", sma, ema, rsi,
               bollinger_upper, bollinger_middle, bollinger_lower
        FROM technical_indicators
        WHERE ticker = %(ticker)s
          AND "interval" = %(interval)s
          AND "timestamp" >= %(start)s
          AND "timestamp" < %(end)s
        ORDER BY "timestamp" ASC
    """

    try:
        with db.warehouse_connection() as conn:
            df = pd.read_sql(query, conn, params={"ticker": ticker, "interval": interval, "start": start, "end": end})
    except Exception:
        log.error("read_technical_indicators_failed", ticker=ticker, interval=interval, exc_info=True)
        raise

    log.info("read_technical_indicators_done", ticker=ticker, interval=interval, row_count=len(df))
    return df


def load_candles(db: WarehouseDB, candles: pd.DataFrame, interval: str) -> int:
    if interval not in CANDLE_TABLES:
        raise ValueError(f"unsupported interval: {interval}")

    if candles.empty:
        return 0

    table = CANDLE_TABLES[interval]
    rows = _clean(candles).to_dict(orient="records")

    stmt = text(
        f"""
        INSERT INTO {table} (ticker, bucket_start, open, high, low, close, volume, tick_count)
        VALUES (:ticker, :bucket_start, :open, :high, :low, :close, :volume, :tick_count)
        ON CONFLICT (ticker, bucket_start) DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume,
            tick_count = EXCLUDED.tick_count
        """
    )

    try:
        with db.warehouse_connection() as conn:
            conn.execute(stmt, rows)
            conn.commit()
    except Exception:
        log.error("load_candles_failed", interval=interval, table=table, exc_info=True)
        raise

    log.info("load_candles_done", interval=interval, table=table, row_count=len(rows))
    return len(rows)


def load_technical_indicators(db: WarehouseDB, indicators: pd.DataFrame) -> int:
    if indicators.empty:
        return 0

    rows = _clean(indicators).to_dict(orient="records")

    stmt = text(
        """
        INSERT INTO technical_indicators
            (ticker, "interval", "timestamp", sma, ema, rsi, bollinger_upper, bollinger_middle, bollinger_lower)
        VALUES
            (:ticker, :interval, :timestamp, :sma, :ema, :rsi, :bollinger_upper, :bollinger_middle, :bollinger_lower)
        ON CONFLICT (ticker, "interval", "timestamp") DO UPDATE SET
            sma = EXCLUDED.sma,
            ema = EXCLUDED.ema,
            rsi = EXCLUDED.rsi,
            bollinger_upper = EXCLUDED.bollinger_upper,
            bollinger_middle = EXCLUDED.bollinger_middle,
            bollinger_lower = EXCLUDED.bollinger_lower,
            computed_at = now()
        """
    )

    try:
        with db.warehouse_connection() as conn:
            conn.execute(stmt, rows)
            conn.commit()
    except Exception:
        log.error("load_technical_indicators_failed", exc_info=True)
        raise

    log.info("load_technical_indicators_done", row_count=len(rows))
    return len(rows)


def load_feature_store(db: WarehouseDB, features: pd.DataFrame) -> int:
    if features.empty:
        return 0

    cleaned = _clean(features).copy()
    cleaned["features"] = cleaned["features"].apply(json.dumps)
    rows = cleaned.to_dict(orient="records")

    stmt = text(
        """
        INSERT INTO feature_store_ai (ticker, "timestamp", features)
        VALUES (:ticker, :timestamp, CAST(:features AS JSONB))
        ON CONFLICT (ticker, "timestamp") DO UPDATE SET
            features = EXCLUDED.features,
            generated_at = now()
        """
    )

    try:
        with db.warehouse_connection() as conn:
            conn.execute(stmt, rows)
            conn.commit()
    except Exception:
        log.error("load_feature_store_failed", exc_info=True)
        raise

    log.info("load_feature_store_done", row_count=len(rows))
    return len(rows)

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from airflow.sdk import dag, task

from etl.config import load_settings
from etl.extract.postgres_source import extract_distinct_tickers
from etl.load.warehouse import read_candles
from etl.storage.warehouse_db import WarehouseDB
from etl.transform.cleaning import detect_gaps, detect_ohlc_anomalies, detect_price_outliers

log = structlog.get_logger()

LOOKBACK = timedelta(days=1)
INTERVALS = ["1m", "5m", "1h"]


@task
def get_tickers() -> list[str]:
    db = WarehouseDB(load_settings())
    try:
        return extract_distinct_tickers(db)
    finally:
        db.dispose()


@task
def check_quality(ticker: str) -> None:
    db = WarehouseDB(load_settings())
    end = datetime.now(timezone.utc)
    start = end - LOOKBACK

    try:
        for interval in INTERVALS:
            candles = read_candles(db, ticker, interval, start, end)
            if candles.empty:
                continue

            anomalies = detect_ohlc_anomalies(candles)
            if not anomalies.empty:
                log.warning("data_quality_ohlc_anomaly", ticker=ticker, interval=interval, row_count=len(anomalies))

            outliers = detect_price_outliers(candles)
            if not outliers.empty:
                log.warning("data_quality_price_outlier", ticker=ticker, interval=interval, row_count=len(outliers))

            gaps = detect_gaps(candles, interval)
            if not gaps.empty:
                log.warning("data_quality_gap_detected", ticker=ticker, interval=interval, gap_count=len(gaps))
    finally:
        db.dispose()


@dag(
    dag_id="data_quality",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "data-quality"],
)
def data_quality_dag():
    tickers = get_tickers()
    check_quality.expand(ticker=tickers)


data_quality_dag()

from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task

from config import load_settings
from extract.postgres_source import extract_distinct_tickers
from load.warehouse import load_technical_indicators, read_candles
from storage.warehouse_db import WarehouseDB
from transform.indicators import compute_indicators


LOOKBACK = timedelta(days=2)
INTERVALS = ["1m", "5m", "1h"]


@task
def get_tickers() -> list[str]:
    db = WarehouseDB(load_settings())
    try:
        return extract_distinct_tickers(db)
    finally:
        db.dispose()


@task
def compute_and_load(ticker: str) -> None:
    db = WarehouseDB(load_settings())
    end = datetime.now(timezone.utc)
    start = end - LOOKBACK

    try:
        for interval in INTERVALS:
            candles = read_candles(db, ticker, interval, start, end)
            indicators = compute_indicators(candles, interval)
            load_technical_indicators(db, indicators)
    finally:
        db.dispose()


@dag(
    dag_id="technical_indicators",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "indicators"],
)
def technical_indicators_dag():
    tickers = get_tickers()
    compute_and_load.expand(ticker=tickers)


technical_indicators_dag()

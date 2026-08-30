from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task

from etl.config import load_settings
from etl.extract.postgres_source import extract_distinct_tickers, extract_stock_prices
from etl.load.warehouse import load_candles
from etl.storage.warehouse_db import WarehouseDB
from etl.transform.candles import aggregate_candles

LOOKBACK = timedelta(hours=2)
INTERVALS = ["1m", "5m", "1h"]


@task
def get_tickers() -> list[str]:
    db = WarehouseDB(load_settings())
    try:
        return extract_distinct_tickers(db)
    finally:
        db.dispose()


@task
def aggregate_and_load(ticker: str) -> None:
    db = WarehouseDB(load_settings())
    end = datetime.now(timezone.utc)
    start = end - LOOKBACK

    try:
        raw = extract_stock_prices(db, ticker, start, end)
        for interval in INTERVALS:
            candles = aggregate_candles(raw, interval)
            load_candles(db, candles, interval)
    finally:
        db.dispose()


@dag(
    dag_id="candle_aggregation",
    schedule="*/5 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "candles"],
)
def candle_aggregation_dag():
    tickers = get_tickers()
    aggregate_and_load.expand(ticker=tickers)


candle_aggregation_dag()

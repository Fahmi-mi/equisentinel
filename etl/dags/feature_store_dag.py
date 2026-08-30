from __future__ import annotations

from datetime import datetime, timedelta, timezone

from airflow.sdk import dag, task

from etl.config import load_settings
from etl.extract.postgres_source import extract_distinct_tickers
from etl.load.warehouse import load_feature_store, read_candles, read_technical_indicators
from etl.storage.warehouse_db import WarehouseDB
from etl.transform.features import build_features

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
def build_and_load_features(ticker: str) -> None:
    db = WarehouseDB(load_settings())
    end = datetime.now(timezone.utc)
    start = end - LOOKBACK

    try:
        candles_1m = read_candles(db, ticker, "1m", start, end)
        if candles_1m.empty:
            return

        latest_candles = candles_1m.sort_values("bucket_start").groupby("ticker", as_index=False).tail(1)

        indicators_by_interval = {}
        for interval in INTERVALS:
            indicators_by_interval[interval] = read_technical_indicators(
                db, ticker, interval, start, end
            )

        features = build_features(latest_candles, indicators_by_interval)
        load_feature_store(db, features)
    finally:
        db.dispose()


@dag(
    dag_id="feature_store",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
    catchup=False,
    tags=["etl", "features"],
)
def feature_store_dag():
    tickers = get_tickers()
    build_and_load_features.expand(ticker=tickers)


feature_store_dag()

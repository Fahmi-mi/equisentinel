from __future__ import annotations

from datetime import datetime

import pandas as pd
import structlog
from sqlalchemy import text

from etl.storage.warehouse_db import WarehouseDB

log = structlog.get_logger()


def extract_stock_prices(
    db: WarehouseDB,
    ticker: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    query = """
        SELECT ticker, open, high, low, close, volume, "timestamp"
        FROM stock_prices
        WHERE ticker = %(ticker)s
          AND "timestamp" >= %(start)s
          AND "timestamp" < %(end)s
        ORDER BY "timestamp" ASC
    """
    try:
        with db.source_connection() as conn:
            df = pd.read_sql(query, conn, params={"ticker": ticker, "start": start, "end": end})
    except Exception:
        log.error("extract_stock_prices_failed", ticker=ticker, start=start, end=end, exc_info=True)
        raise

    log.info("extract_stock_prices_done", ticker=ticker, row_count=len(df))
    return df


def extract_news_articles(
    db: WarehouseDB,
    ticker: str,
    start: datetime,
    end: datetime,
) -> pd.DataFrame:
    query = """
        SELECT id, ticker, headline, body, source, published_at
        FROM news_articles
        WHERE ticker = %(ticker)s
          AND published_at >= %(start)s
          AND published_at < %(end)s
        ORDER BY published_at ASC
    """
    try:
        with db.source_connection() as conn:
            df = pd.read_sql(query, conn, params={"ticker": ticker, "start": start, "end": end})
    except Exception:
        log.error("extract_news_articles_failed", ticker=ticker, start=start, end=end, exc_info=True)
        raise

    log.info("extract_news_articles_done", ticker=ticker, row_count=len(df))
    return df


def extract_distinct_tickers(db: WarehouseDB) -> list[str]:
    try:
        with db.source_connection() as conn:
            result = conn.execute(text("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker"))
            tickers = [row[0] for row in result]
    except Exception:
        log.error("extract_distinct_tickers_failed", exc_info=True)
        raise

    log.info("extract_distinct_tickers_done", ticker_count=len(tickers))
    return tickers

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS stock_prices (
    ticker TEXT NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    UNIQUE (ticker, "timestamp")
);

SELECT create_hypertable('stock_prices', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_timestamp
    ON stock_prices (ticker, "timestamp" DESC);

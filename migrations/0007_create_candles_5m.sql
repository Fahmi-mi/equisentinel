CREATE TABLE IF NOT EXISTS candles_5m (
    ticker TEXT NOT NULL,
    bucket_start TIMESTAMPTZ NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL,
    tick_count INTEGER NOT NULL,
    UNIQUE (ticker, bucket_start)
);

SELECT create_hypertable('candles_5m', 'bucket_start', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_candles_5m_ticker_bucket_start
    ON candles_5m (ticker, bucket_start DESC);

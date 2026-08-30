CREATE TABLE IF NOT EXISTS candles_1h (
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

SELECT create_hypertable('candles_1h', 'bucket_start', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_candles_1h_ticker_bucket_start
    ON candles_1h (ticker, bucket_start DESC);

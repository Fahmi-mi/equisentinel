CREATE TABLE IF NOT EXISTS technical_indicators (
    ticker TEXT NOT NULL,
    "interval" TEXT NOT NULL CHECK ("interval" IN ('1m', '5m', '1h')),
    "timestamp" TIMESTAMPTZ NOT NULL,
    sma DOUBLE PRECISION,
    ema DOUBLE PRECISION,
    rsi DOUBLE PRECISION,
    bollinger_upper DOUBLE PRECISION,
    bollinger_middle DOUBLE PRECISION,
    bollinger_lower DOUBLE PRECISION,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ticker, "interval", "timestamp")
);

SELECT create_hypertable('technical_indicators', 'timestamp', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_technical_indicators_ticker_interval_timestamp
    ON technical_indicators (ticker, "interval", "timestamp" DESC);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id UUID NOT NULL UNIQUE,
    ticker TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    price_change_pct DOUBLE PRECISION NOT NULL,
    volume_ratio DOUBLE PRECISION NOT NULL,
    critical BOOLEAN NOT NULL DEFAULT false,
    detected_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_anomaly_events_ticker_detected_at
    ON anomaly_events (ticker, detected_at DESC);

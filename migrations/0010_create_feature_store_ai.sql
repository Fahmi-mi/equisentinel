CREATE TABLE IF NOT EXISTS feature_store_ai (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    features JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ticker, "timestamp")
);

CREATE INDEX IF NOT EXISTS idx_feature_store_ai_ticker_timestamp
    ON feature_store_ai (ticker, "timestamp" DESC);

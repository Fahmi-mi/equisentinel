CREATE TABLE IF NOT EXISTS news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL,
    headline TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_news_articles_ticker_published_at
    ON news_articles (ticker, published_at DESC);

package postgres

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
)

type Client struct {
	pool *pgxpool.Pool
}

func Connect(ctx context.Context, url string) (*Client, error) {
	pool, err := pgxpool.New(ctx, url)
	if err != nil {
		return nil, err
	}
	return &Client{pool: pool}, nil
}

func (c *Client) Close() {
	c.pool.Close()
}

func (c *Client) InsertAIAnalysis(
	ctx context.Context,
	correlationID, ticker, summary, sentiment, riskLevel, modelUsed string,
	latencyMs int32,
) error {
	_, err := c.pool.Exec(ctx, `
		INSERT INTO ai_analyses (correlation_id, ticker, summary, sentiment, risk_level, model_used, latency_ms)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (correlation_id) DO NOTHING
	`, correlationID, ticker, summary, sentiment, riskLevel, modelUsed, latencyMs)
	return err
}

func (c *Client) InsertNewsArticle(
	ctx context.Context,
	id, ticker, headline, body, source string,
	publishedAt time.Time,
) error {
	_, err := c.pool.Exec(ctx, `
		INSERT INTO news_articles (id, ticker, headline, body, source, published_at)
		VALUES ($1, $2, $3, $4, $5, $6)
		ON CONFLICT (id) DO NOTHING
	`, id, ticker, headline, body, source, publishedAt)
	return err
}

func (c *Client) InsertAnomalyEvent(
	ctx context.Context,
	correlationID, ticker, triggerType string,
	priceChangePct, volumeRatio float64,
	critical bool,
	detectedAt time.Time,
) error {
	_, err := c.pool.Exec(ctx, `
		INSERT INTO anomaly_events (correlation_id, ticker, trigger_type, price_change_pct, volume_ratio, critical, detected_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (correlation_id) DO NOTHING
	`, correlationID, ticker, triggerType, priceChangePct, volumeRatio, critical, detectedAt)
	return err
}

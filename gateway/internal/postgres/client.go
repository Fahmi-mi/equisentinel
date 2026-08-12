package postgres

import (
	"context"

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

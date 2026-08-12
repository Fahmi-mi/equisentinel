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

type AIAnalysisRow struct {
	CorrelationID string
	Ticker        string
	Summary       string
	Sentiment     string
	RiskLevel     string
	ModelUsed     string
	LatencyMs     int32
	CreatedAt     time.Time
}

func (c *Client) QueryAIAnalyses(ctx context.Context, ticker string, limit int) ([]AIAnalysisRow, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT correlation_id, ticker, summary, sentiment, risk_level, model_used, latency_ms, created_at FROM (
			SELECT correlation_id, ticker, summary, sentiment, risk_level, model_used, latency_ms, created_at
			FROM ai_analyses
			WHERE ticker = $1
			ORDER BY created_at DESC
			LIMIT $2
		) recent
		ORDER BY created_at ASC
	`, ticker, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []AIAnalysisRow
	for rows.Next() {
		var r AIAnalysisRow
		if err := rows.Scan(
			&r.CorrelationID, &r.Ticker, &r.Summary, &r.Sentiment,
			&r.RiskLevel, &r.ModelUsed, &r.LatencyMs, &r.CreatedAt,
		); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

func (c *Client) InsertStockPrice(
	ctx context.Context,
	ticker string,
	open, high, low, close float64,
	volume int64,
	timestamp time.Time,
) error {
	_, err := c.pool.Exec(ctx, `
		INSERT INTO stock_prices (ticker, open, high, low, close, volume, timestamp)
		VALUES ($1, $2, $3, $4, $5, $6, $7)
		ON CONFLICT (ticker, timestamp) DO NOTHING
	`, ticker, open, high, low, close, volume, timestamp)
	return err
}

type StockPriceRow struct {
	Ticker    string
	Open      float64
	High      float64
	Low       float64
	Close     float64
	Volume    int64
	Timestamp time.Time
}

func (c *Client) QueryStockPrices(ctx context.Context, ticker string, limit int) ([]StockPriceRow, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT ticker, open, high, low, close, volume, timestamp FROM (
			SELECT ticker, open, high, low, close, volume, timestamp
			FROM stock_prices
			WHERE ticker = $1
			ORDER BY timestamp DESC
			LIMIT $2
		) recent
		ORDER BY timestamp ASC
	`, ticker, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []StockPriceRow
	for rows.Next() {
		var r StockPriceRow
		if err := rows.Scan(&r.Ticker, &r.Open, &r.High, &r.Low, &r.Close, &r.Volume, &r.Timestamp); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

package postgres

import (
	"context"
	"fmt"
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
	Feedback      *string
}

func (c *Client) QueryAIAnalyses(ctx context.Context, ticker string, limit int) ([]AIAnalysisRow, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT correlation_id, ticker, summary, sentiment, risk_level, model_used, latency_ms, created_at, feedback_value FROM (
			SELECT a.correlation_id, a.ticker, a.summary, a.sentiment, a.risk_level, a.model_used, a.latency_ms,
				a.created_at, f.feedback_value
			FROM ai_analyses a
			LEFT JOIN user_feedback f ON f.correlation_id = a.correlation_id
			WHERE a.ticker = $1
			ORDER BY a.created_at DESC
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
			&r.RiskLevel, &r.ModelUsed, &r.LatencyMs, &r.CreatedAt, &r.Feedback,
		); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

func (c *Client) UpsertUserFeedback(ctx context.Context, correlationID, feedbackValue string) error {
	_, err := c.pool.Exec(ctx, `
		INSERT INTO user_feedback (correlation_id, feedback_value, submitted_at)
		VALUES ($1, $2, now())
		ON CONFLICT (correlation_id) DO UPDATE SET feedback_value = $2, submitted_at = now()
	`, correlationID, feedbackValue)
	return err
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

var candleTables = map[string]string{
	"1m": "candles_1m",
	"5m": "candles_5m",
	"1h": "candles_1h",
}

func candleTable(interval string) (string, bool) {
	table, ok := candleTables[interval]
	return table, ok
}

type CandleRow struct {
	Ticker      string
	BucketStart time.Time
	Open        float64
	High        float64
	Low         float64
	Close       float64
	Volume      int64
	TickCount   int32
}

func (c *Client) QueryCandles(ctx context.Context, ticker, interval string, limit int) ([]CandleRow, error) {
	table, ok := candleTable(interval)
	if !ok {
		return nil, fmt.Errorf("unsupported interval: %s", interval)
	}

	rows, err := c.pool.Query(ctx, fmt.Sprintf(`
		SELECT ticker, bucket_start, open, high, low, close, volume, tick_count FROM (
			SELECT ticker, bucket_start, open, high, low, close, volume, tick_count
			FROM %s
			WHERE ticker = $1
			ORDER BY bucket_start DESC
			LIMIT $2
		) recent
		ORDER BY bucket_start ASC
	`, table), ticker, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []CandleRow
	for rows.Next() {
		var r CandleRow
		if err := rows.Scan(&r.Ticker, &r.BucketStart, &r.Open, &r.High, &r.Low, &r.Close, &r.Volume, &r.TickCount); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

type IndicatorRow struct {
	Ticker          string
	Interval        string
	Timestamp       time.Time
	SMA             *float64
	EMA             *float64
	RSI             *float64
	BollingerUpper  *float64
	BollingerMiddle *float64
	BollingerLower  *float64
}

func (c *Client) QueryTechnicalIndicators(ctx context.Context, ticker, interval string, limit int) ([]IndicatorRow, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT ticker, "interval", "timestamp", sma, ema, rsi,
		       bollinger_upper, bollinger_middle, bollinger_lower FROM (
			SELECT ticker, "interval", "timestamp", sma, ema, rsi,
			       bollinger_upper, bollinger_middle, bollinger_lower
			FROM technical_indicators
			WHERE ticker = $1 AND "interval" = $2
			ORDER BY "timestamp" DESC
			LIMIT $3
		) recent
		ORDER BY "timestamp" ASC
	`, ticker, interval, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []IndicatorRow
	for rows.Next() {
		var r IndicatorRow
		if err := rows.Scan(&r.Ticker, &r.Interval, &r.Timestamp, &r.SMA, &r.EMA, &r.RSI, &r.BollingerUpper, &r.BollingerMiddle, &r.BollingerLower); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

func (c *Client) QueryLatestIndicators(ctx context.Context, interval string) ([]IndicatorRow, error) {
	rows, err := c.pool.Query(ctx, `
		SELECT DISTINCT ON (ticker) ticker, "interval", "timestamp", sma, ema, rsi,
		       bollinger_upper, bollinger_middle, bollinger_lower
		FROM technical_indicators
		WHERE "interval" = $1
		ORDER BY ticker, "timestamp" DESC
	`, interval)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var result []IndicatorRow
	for rows.Next() {
		var r IndicatorRow
		if err := rows.Scan(&r.Ticker, &r.Interval, &r.Timestamp, &r.SMA, &r.EMA, &r.RSI, &r.BollingerUpper, &r.BollingerMiddle, &r.BollingerLower); err != nil {
			return nil, err
		}
		result = append(result, r)
	}
	return result, rows.Err()
}

package main

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/nats-io/nats.go"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"google.golang.org/protobuf/encoding/protojson"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"

	"github.com/Fahmi-mi/equisentinel/gateway/internal/anomaly"
	"github.com/Fahmi-mi/equisentinel/gateway/internal/config"
	"github.com/Fahmi-mi/equisentinel/gateway/internal/health"
	"github.com/Fahmi-mi/equisentinel/gateway/internal/natsclient"
	"github.com/Fahmi-mi/equisentinel/gateway/internal/postgres"
	pb "github.com/Fahmi-mi/equisentinel/gateway/internal/proto"
	"github.com/Fahmi-mi/equisentinel/gateway/internal/ws"
)

const (
	quotesStream        = "STOCK_QUOTES"
	quotesSubject       = "stock.quotes.*"
	quotesConsumer      = "gateway-quotes"
	anomalyStream       = "STOCK_ANOMALY"
	anomalySubject      = "stock.anomaly"
	anomalyCriticalSubj = "stock.anomaly.critical"
	resultsStream       = "STOCK_RESULTS"
	resultsSubject      = "stock.results"
	resultsConsumer     = "gateway-results"
	newsStream          = "STOCK_NEWS"
	newsSubject         = "stock.news.*"
	newsConsumer        = "gateway-news"
	streamMaxAge        = 24 * time.Hour
)

var pbJSONMarshaler = protojson.MarshalOptions{EmitUnpopulated: true}

func wrapEnvelope(msgType string, data []byte) ([]byte, error) {
	return json.Marshal(struct {
		Type string          `json:"type"`
		Data json.RawMessage `json:"data"`
	}{Type: msgType, Data: data})
}

func main() {
	zerolog.TimeFieldFormat = time.RFC3339
	cfg := config.Load()

	nc, err := natsclient.Connect(cfg.NATSURL)
	if err != nil {
		log.Fatal().Err(err).Msg("nats_connect_failed")
	}
	defer nc.Close()

	pg, err := postgres.Connect(context.Background(), cfg.DatabaseURL)
	if err != nil {
		log.Fatal().Err(err).Msg("postgres_connect_failed")
	}
	defer pg.Close()

	if err := nc.EnsureStream(anomalyStream, []string{anomalySubject, anomalyCriticalSubj}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_anomaly_stream_failed")
	}
	if err := nc.EnsureStream(quotesStream, []string{quotesSubject}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_quotes_stream_failed")
	}
	if err := nc.EnsureStream(resultsStream, []string{resultsSubject}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_results_stream_failed")
	}
	if err := nc.EnsureStream(newsStream, []string{newsSubject}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_news_stream_failed")
	}

	hub := ws.NewHub(cfg.AllowedOrigins)
	detector := anomaly.NewDetector(cfg.PriceChangePctThreshold, cfg.VolumeRatioThreshold, cfg.CriticalPriceChangePct)
	debouncer := anomaly.NewDebouncer(time.Duration(cfg.DebounceWindowSeconds) * time.Second)

	js := nc.JetStream()
	sub, err := js.Subscribe(quotesSubject, func(msg *nats.Msg) {
		handleQuote(msg, hub, detector, debouncer, js, pg)
	}, nats.Durable(quotesConsumer), nats.ManualAck())
	if err != nil {
		log.Fatal().Err(err).Msg("subscribe_quotes_failed")
	}
	defer sub.Unsubscribe()

	resultsSub, err := js.Subscribe(resultsSubject, func(msg *nats.Msg) {
		handleAIAnalysis(msg, hub, pg)
	}, nats.Durable(resultsConsumer), nats.ManualAck())
	if err != nil {
		log.Fatal().Err(err).Msg("subscribe_results_failed")
	}
	defer resultsSub.Unsubscribe()

	newsSub, err := js.Subscribe(newsSubject, func(msg *nats.Msg) {
		handleNewsArticle(msg, pg)
	}, nats.Durable(newsConsumer), nats.ManualAck())
	if err != nil {
		log.Fatal().Err(err).Msg("subscribe_news_failed")
	}
	defer newsSub.Unsubscribe()

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		if err := hub.ServeWS(w, r); err != nil {
			log.Warn().Err(err).Msg("ws_upgrade_failed")
		}
	})
	mux.HandleFunc("/health", health.Handler(func() health.Status {
		return health.Status{NATSConnected: nc.IsConnected(), WSClients: hub.ClientCount()}
	}))
	mux.HandleFunc("/history", func(w http.ResponseWriter, r *http.Request) {
		handleHistory(w, r, pg)
	})
	mux.HandleFunc("/analyses", func(w http.ResponseWriter, r *http.Request) {
		handleAnalysesHistory(w, r, pg)
	})
	mux.HandleFunc("/feedback", func(w http.ResponseWriter, r *http.Request) {
		handleFeedback(w, r, pg)
	})

	srv := &http.Server{Addr: ":" + cfg.HTTPPort, Handler: mux}

	go func() {
		log.Info().Str("addr", srv.Addr).Msg("http_server_starting")
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("http_server_failed")
		}
	}()

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop

	log.Info().Msg("shutting_down")
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	srv.Shutdown(ctx)
}

func handleQuote(msg *nats.Msg, hub *ws.Hub, detector *anomaly.Detector, debouncer *anomaly.Debouncer, js nats.JetStreamContext, pg *postgres.Client) {
	defer msg.Ack()

	var quote pb.StockQuote
	if err := proto.Unmarshal(msg.Data, &quote); err != nil {
		log.Error().Err(err).Msg("quote_unmarshal_failed")
		return
	}

	quoteJSON, err := pbJSONMarshaler.Marshal(&quote)
	if err != nil {
		log.Error().Err(err).Msg("quote_marshal_json_failed")
	} else if envelope, err := wrapEnvelope("quote", quoteJSON); err != nil {
		log.Error().Err(err).Msg("quote_envelope_failed")
	} else {
		hub.Broadcast(envelope)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	if err := pg.InsertStockPrice(
		ctx, quote.Ticker, quote.Open, quote.High, quote.Low, quote.Close,
		quote.Volume, quote.Timestamp.AsTime(),
	); err != nil {
		log.Error().Err(err).Msg("quote_persist_failed")
	}
	cancel()

	results := detector.Evaluate(anomaly.Quote{
		Ticker:    quote.Ticker,
		Close:     quote.Close,
		Volume:    quote.Volume,
		Timestamp: quote.Timestamp.AsTime(),
	})

	for _, r := range results {
		key := r.Ticker + ":" + string(r.TriggerType)
		if !debouncer.Allow(key, r.DetectedAt) {
			continue
		}
		publishAnomaly(js, pg, r)
	}
}

func publishAnomaly(js nats.JetStreamContext, pg *postgres.Client, r anomaly.Result) {
	event := &pb.AnomalyEvent{
		CorrelationId:  uuid.NewString(),
		Ticker:         r.Ticker,
		TriggerType:    string(r.TriggerType),
		PriceChangePct: r.PriceChangePct,
		VolumeRatio:    r.VolumeRatio,
		DetectedAt:     timestamppb.New(r.DetectedAt),
	}

	data, err := proto.Marshal(event)
	if err != nil {
		log.Error().Err(err).Msg("anomaly_marshal_failed")
		return
	}

	subject := anomalySubject
	if r.Critical {
		subject = anomalyCriticalSubj
	}

	if _, err := js.Publish(subject, data); err != nil {
		log.Error().Err(err).Msg("anomaly_publish_failed")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := pg.InsertAnomalyEvent(
		ctx, event.CorrelationId, event.Ticker, event.TriggerType,
		event.PriceChangePct, event.VolumeRatio, r.Critical, r.DetectedAt,
	); err != nil {
		log.Error().Err(err).Msg("anomaly_persist_failed")
	}

	log.Info().
		Str("correlation_id", event.CorrelationId).
		Str("ticker", event.Ticker).
		Str("trigger_type", event.TriggerType).
		Bool("critical", r.Critical).
		Msg("anomaly_detected")
}

const defaultHistoryLimit = 500

type historyQuote struct {
	Ticker    string  `json:"ticker"`
	Open      float64 `json:"open"`
	High      float64 `json:"high"`
	Low       float64 `json:"low"`
	Close     float64 `json:"close"`
	Volume    string  `json:"volume"`
	Timestamp string  `json:"timestamp"`
}

func handleHistory(w http.ResponseWriter, r *http.Request, pg *postgres.Client) {
	ticker := r.URL.Query().Get("ticker")
	if ticker == "" {
		http.Error(w, "ticker is required", http.StatusBadRequest)
		return
	}

	limit := defaultHistoryLimit
	if v := r.URL.Query().Get("limit"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 && parsed <= defaultHistoryLimit {
			limit = parsed
		}
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	rows, err := pg.QueryStockPrices(ctx, ticker, limit)
	if err != nil {
		log.Error().Err(err).Msg("history_query_failed")
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	quotes := make([]historyQuote, len(rows))
	for i, row := range rows {
		quotes[i] = historyQuote{
			Ticker:    row.Ticker,
			Open:      row.Open,
			High:      row.High,
			Low:       row.Low,
			Close:     row.Close,
			Volume:    strconv.FormatInt(row.Volume, 10),
			Timestamp: row.Timestamp.UTC().Format(time.RFC3339),
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(struct {
		Quotes []historyQuote `json:"quotes"`
	}{Quotes: quotes})
}

const defaultAnalysesLimit = 200

type historyAnalysis struct {
	CorrelationID string  `json:"correlationId"`
	Ticker        string  `json:"ticker"`
	Summary       string  `json:"summary"`
	Sentiment     string  `json:"sentiment"`
	RiskLevel     string  `json:"riskLevel"`
	ModelUsed     string  `json:"modelUsed"`
	LatencyMs     int32   `json:"latencyMs"`
	CreatedAt     string  `json:"createdAt"`
	Feedback      *string `json:"feedback,omitempty"`
}

func handleAnalysesHistory(w http.ResponseWriter, r *http.Request, pg *postgres.Client) {
	ticker := r.URL.Query().Get("ticker")
	if ticker == "" {
		http.Error(w, "ticker is required", http.StatusBadRequest)
		return
	}

	limit := defaultAnalysesLimit
	if v := r.URL.Query().Get("limit"); v != "" {
		if parsed, err := strconv.Atoi(v); err == nil && parsed > 0 && parsed <= defaultAnalysesLimit {
			limit = parsed
		}
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	rows, err := pg.QueryAIAnalyses(ctx, ticker, limit)
	if err != nil {
		log.Error().Err(err).Msg("analyses_history_query_failed")
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	analyses := make([]historyAnalysis, len(rows))
	for i, row := range rows {
		analyses[i] = historyAnalysis{
			CorrelationID: row.CorrelationID,
			Ticker:        row.Ticker,
			Summary:       row.Summary,
			Sentiment:     row.Sentiment,
			RiskLevel:     row.RiskLevel,
			ModelUsed:     row.ModelUsed,
			LatencyMs:     row.LatencyMs,
			CreatedAt:     row.CreatedAt.UTC().Format(time.RFC3339),
			Feedback:      row.Feedback,
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(struct {
		Analyses []historyAnalysis `json:"analyses"`
	}{Analyses: analyses})
}

type feedbackRequest struct {
	CorrelationID string `json:"correlationId"`
	FeedbackValue string `json:"feedbackValue"`
}

func handleFeedback(w http.ResponseWriter, r *http.Request, pg *postgres.Client) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req feedbackRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}
	if req.CorrelationID == "" || (req.FeedbackValue != "ACCURATE" && req.FeedbackValue != "INACCURATE") {
		http.Error(w, "correlationId and a valid feedbackValue are required", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	if err := pg.UpsertUserFeedback(ctx, req.CorrelationID, req.FeedbackValue); err != nil {
		log.Error().Err(err).Msg("feedback_persist_failed")
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func handleNewsArticle(msg *nats.Msg, pg *postgres.Client) {
	defer msg.Ack()

	var article pb.NewsArticle
	if err := proto.Unmarshal(msg.Data, &article); err != nil {
		log.Error().Err(err).Msg("news_unmarshal_failed")
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := pg.InsertNewsArticle(
		ctx, article.Id, article.Ticker, article.Headline, article.Body, article.Source,
		article.PublishedAt.AsTime(),
	); err != nil {
		log.Error().Err(err).Msg("news_persist_failed")
		return
	}

	log.Info().
		Str("ticker", article.Ticker).
		Str("headline", article.Headline).
		Msg("news_persisted")
}

func handleAIAnalysis(msg *nats.Msg, hub *ws.Hub, pg *postgres.Client) {
	defer msg.Ack()

	var analysis pb.AiAnalysis
	if err := proto.Unmarshal(msg.Data, &analysis); err != nil {
		log.Error().Err(err).Msg("analysis_unmarshal_failed")
		return
	}

	sentiment := strings.TrimPrefix(analysis.Sentiment.String(), "SENTIMENT_")
	riskLevel := strings.TrimPrefix(analysis.RiskLevel.String(), "RISK_LEVEL_")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := pg.InsertAIAnalysis(
		ctx, analysis.CorrelationId, analysis.Ticker, analysis.Summary,
		sentiment, riskLevel, analysis.ModelUsed, analysis.LatencyMs,
	); err != nil {
		log.Error().Err(err).Msg("analysis_persist_failed")
	}

	analysisJSON, err := pbJSONMarshaler.Marshal(&analysis)
	if err != nil {
		log.Error().Err(err).Msg("analysis_marshal_json_failed")
		return
	}
	envelope, err := wrapEnvelope("ai_analysis", analysisJSON)
	if err != nil {
		log.Error().Err(err).Msg("analysis_envelope_failed")
		return
	}
	hub.Broadcast(envelope)

	log.Info().
		Str("correlation_id", analysis.CorrelationId).
		Str("ticker", analysis.Ticker).
		Str("sentiment", sentiment).
		Msg("analysis_received")
}

package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
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
	streamMaxAge        = 24 * time.Hour
)

var quoteJSONMarshaler = protojson.MarshalOptions{EmitUnpopulated: true}

func main() {
	zerolog.TimeFieldFormat = time.RFC3339
	cfg := config.Load()

	nc, err := natsclient.Connect(cfg.NATSURL)
	if err != nil {
		log.Fatal().Err(err).Msg("nats_connect_failed")
	}
	defer nc.Close()

	if err := nc.EnsureStream(anomalyStream, []string{anomalySubject, anomalyCriticalSubj}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_anomaly_stream_failed")
	}
	if err := nc.EnsureStream(quotesStream, []string{quotesSubject}, streamMaxAge); err != nil {
		log.Fatal().Err(err).Msg("ensure_quotes_stream_failed")
	}

	hub := ws.NewHub()
	detector := anomaly.NewDetector(cfg.PriceChangePctThreshold, cfg.VolumeRatioThreshold, cfg.CriticalPriceChangePct)
	debouncer := anomaly.NewDebouncer(time.Duration(cfg.DebounceWindowSeconds) * time.Second)

	js := nc.JetStream()
	sub, err := js.Subscribe(quotesSubject, func(msg *nats.Msg) {
		handleQuote(msg, hub, detector, debouncer, js)
	}, nats.Durable(quotesConsumer), nats.ManualAck())
	if err != nil {
		log.Fatal().Err(err).Msg("subscribe_quotes_failed")
	}
	defer sub.Unsubscribe()

	mux := http.NewServeMux()
	mux.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		if err := hub.ServeWS(w, r); err != nil {
			log.Warn().Err(err).Msg("ws_upgrade_failed")
		}
	})
	mux.HandleFunc("/health", health.Handler(func() health.Status {
		return health.Status{NATSConnected: nc.IsConnected(), WSClients: hub.ClientCount()}
	}))

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

func handleQuote(msg *nats.Msg, hub *ws.Hub, detector *anomaly.Detector, debouncer *anomaly.Debouncer, js nats.JetStreamContext) {
	defer msg.Ack()

	var quote pb.StockQuote
	if err := proto.Unmarshal(msg.Data, &quote); err != nil {
		log.Error().Err(err).Msg("quote_unmarshal_failed")
		return
	}

	quoteJSON, err := quoteJSONMarshaler.Marshal(&quote)
	if err != nil {
		log.Error().Err(err).Msg("quote_marshal_json_failed")
	} else {
		hub.Broadcast(quoteJSON)
	}

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
		publishAnomaly(js, r)
	}
}

func publishAnomaly(js nats.JetStreamContext, r anomaly.Result) {
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

	log.Info().
		Str("correlation_id", event.CorrelationId).
		Str("ticker", event.Ticker).
		Str("trigger_type", event.TriggerType).
		Bool("critical", r.Critical).
		Msg("anomaly_detected")
}

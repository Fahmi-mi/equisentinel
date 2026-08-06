package proto

import (
	"testing"
	"time"

	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"
)

func TestStockQuoteRoundTrip(t *testing.T) {
	original := &StockQuote{
		Ticker:    "BBCA",
		Open:      9000,
		High:      9100,
		Low:       8950,
		Close:     9050,
		Volume:    1500000,
		Timestamp: timestamppb.New(time.Now().UTC()),
	}

	data, err := proto.Marshal(original)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	decoded := &StockQuote{}
	if err := proto.Unmarshal(data, decoded); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if decoded.Ticker != original.Ticker || decoded.Close != original.Close || decoded.Volume != original.Volume {
		t.Errorf("roundtrip mismatch: got %+v, want %+v", decoded, original)
	}
}

func TestAnomalyEventRoundTrip(t *testing.T) {
	original := &AnomalyEvent{
		CorrelationId:  "test-correlation-id",
		Ticker:         "GOTO",
		TriggerType:    "PRICE_CHANGE",
		PriceChangePct: -7.2,
		VolumeRatio:    0,
		DetectedAt:     timestamppb.New(time.Now().UTC()),
	}

	data, err := proto.Marshal(original)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	decoded := &AnomalyEvent{}
	if err := proto.Unmarshal(data, decoded); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	if decoded.CorrelationId != original.CorrelationId || decoded.TriggerType != original.TriggerType {
		t.Errorf("roundtrip mismatch: got %+v, want %+v", decoded, original)
	}
}

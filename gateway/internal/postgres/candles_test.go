package postgres

import "testing"

func TestCandleTableValidIntervals(t *testing.T) {
	for _, interval := range []string{"1m", "5m", "1h"} {
		table, ok := candleTable(interval)
		if !ok {
			t.Fatalf("expected interval %q to be supported", interval)
		}
		expected := "candles_" + interval
		if table != expected {
			t.Fatalf("expected table %q, got %q", expected, table)
		}
	}
}

func TestCandleTableRejectsUnknownInterval(t *testing.T) {
	for _, interval := range []string{"3m", "1d", "", "candles_1m; DROP TABLE candles_1m"} {
		if _, ok := candleTable(interval); ok {
			t.Fatalf("expected interval %q to be rejected", interval)
		}
	}
}

package anomaly

import (
	"testing"
	"time"
)

func TestPriceChangeThreshold(t *testing.T) {
	base := time.Now()

	cases := []struct {
		name       string
		changePct  float64
		wantDetect bool
	}{
		{"below_threshold", 2.0, false},
		{"at_threshold", 3.0, false},
		{"above_threshold", 3.5, true},
		{"drop_above_threshold", -4.0, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			d := NewDetector(3.0, 5.0, 5.0)
			openPrice := 1000.0
			d.Evaluate(Quote{Ticker: "BBCA", Close: openPrice, Volume: 100, Timestamp: base})

			closePrice := openPrice * (1 + tc.changePct/100)
			results := d.Evaluate(Quote{Ticker: "BBCA", Close: closePrice, Volume: 100, Timestamp: base.Add(10 * time.Second)})

			found := false
			for _, r := range results {
				if r.TriggerType == TriggerPriceChange {
					found = true
				}
			}
			if found != tc.wantDetect {
				t.Errorf("changePct=%v: got detect=%v, want %v", tc.changePct, found, tc.wantDetect)
			}
		})
	}
}

func TestPriceChangeOutsideWindowIsIgnored(t *testing.T) {
	d := NewDetector(3.0, 5.0, 5.0)
	base := time.Now()

	d.Evaluate(Quote{Ticker: "BBCA", Close: 1000, Volume: 100, Timestamp: base})
	results := d.Evaluate(Quote{Ticker: "BBCA", Close: 2000, Volume: 100, Timestamp: base.Add(2 * time.Minute)})

	for _, r := range results {
		if r.TriggerType == TriggerPriceChange {
			t.Errorf("expected old quote outside 1-minute window to be evicted, but price change was still detected")
		}
	}
}

func TestCriticalPriceChangeFlag(t *testing.T) {
	d := NewDetector(3.0, 5.0, 5.0)
	base := time.Now()

	d.Evaluate(Quote{Ticker: "GOTO", Close: 1000, Volume: 100, Timestamp: base})
	results := d.Evaluate(Quote{Ticker: "GOTO", Close: 930, Volume: 100, Timestamp: base.Add(10 * time.Second)})

	if len(results) != 1 || !results[0].Critical {
		t.Errorf("expected a critical price change result for a -7%% move, got %+v", results)
	}
}

func TestVolumeSpikeThreshold(t *testing.T) {
	d := NewDetector(3.0, 5.0, 5.0)
	base := time.Now()

	for i := 0; i < 5; i++ {
		d.Evaluate(Quote{Ticker: "TLKM", Close: 100, Volume: 1000, Timestamp: base.Add(time.Duration(i) * time.Minute)})
	}

	results := d.Evaluate(Quote{Ticker: "TLKM", Close: 100, Volume: 6000, Timestamp: base.Add(6 * time.Minute)})

	found := false
	for _, r := range results {
		if r.TriggerType == TriggerVolumeSpike {
			found = true
		}
	}
	if !found {
		t.Errorf("expected volume spike to be detected for 6x average volume")
	}
}

package anomaly

import (
	"testing"
	"time"
)

func TestDebouncerSuppressesWithinWindow(t *testing.T) {
	d := NewDebouncer(30 * time.Second)
	base := time.Now()

	if !d.Allow("BBCA:PRICE_CHANGE", base) {
		t.Fatal("expected first event to be allowed")
	}
	if d.Allow("BBCA:PRICE_CHANGE", base.Add(10*time.Second)) {
		t.Error("expected second event within 30s window to be suppressed")
	}
}

func TestDebouncerAllowsAfterWindow(t *testing.T) {
	d := NewDebouncer(30 * time.Second)
	base := time.Now()

	d.Allow("BBCA:PRICE_CHANGE", base)
	if !d.Allow("BBCA:PRICE_CHANGE", base.Add(31*time.Second)) {
		t.Error("expected event after 30s window to be allowed")
	}
}

func TestDebouncerTracksKeysIndependently(t *testing.T) {
	d := NewDebouncer(30 * time.Second)
	base := time.Now()

	d.Allow("BBCA:PRICE_CHANGE", base)
	if !d.Allow("BBCA:VOLUME_SPIKE", base) {
		t.Error("expected different trigger type on the same ticker to be tracked independently")
	}
	if !d.Allow("GOTO:PRICE_CHANGE", base) {
		t.Error("expected same trigger type on a different ticker to be tracked independently")
	}
}

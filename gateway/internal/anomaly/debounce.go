package anomaly

import (
	"sync"
	"time"
)

type Debouncer struct {
	mu       sync.Mutex
	lastSeen map[string]time.Time
	window   time.Duration
}

func NewDebouncer(window time.Duration) *Debouncer {
	return &Debouncer{
		lastSeen: make(map[string]time.Time),
		window:   window,
	}
}

func (d *Debouncer) Allow(key string, now time.Time) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	last, seen := d.lastSeen[key]
	if seen && now.Sub(last) < d.window {
		return false
	}

	d.lastSeen[key] = now
	return true
}

package anomaly

import (
	"math"
	"sync"
	"time"
)

type TriggerType string

const (
	TriggerPriceChange TriggerType = "PRICE_CHANGE"
	TriggerVolumeSpike TriggerType = "VOLUME_SPIKE"

	priceWindow  = time.Minute
	volumeWindow = 20 * time.Minute
)

type Quote struct {
	Ticker    string
	Close     float64
	Volume    int64
	Timestamp time.Time
}

type Result struct {
	Ticker         string
	TriggerType    TriggerType
	PriceChangePct float64
	VolumeRatio    float64
	DetectedAt     time.Time
	Critical       bool
}

type tickerState struct {
	priceHistory  []Quote
	volumeHistory []Quote
}

type Detector struct {
	mu                sync.Mutex
	states            map[string]*tickerState
	priceThresholdPct float64
	volumeThreshold   float64
	criticalPct       float64
}

func NewDetector(priceThresholdPct, volumeThreshold, criticalPct float64) *Detector {
	return &Detector{
		states:            make(map[string]*tickerState),
		priceThresholdPct: priceThresholdPct,
		volumeThreshold:   volumeThreshold,
		criticalPct:       criticalPct,
	}
}

func (d *Detector) Evaluate(q Quote) []Result {
	d.mu.Lock()
	defer d.mu.Unlock()

	st, ok := d.states[q.Ticker]
	if !ok {
		st = &tickerState{}
		d.states[q.Ticker] = st
	}

	st.priceHistory = append(evict(st.priceHistory, q.Timestamp, priceWindow), q)
	st.volumeHistory = append(evict(st.volumeHistory, q.Timestamp, volumeWindow), q)

	var results []Result

	if r, ok := d.checkPriceChange(q, st.priceHistory); ok {
		results = append(results, r)
	}
	if r, ok := d.checkVolumeSpike(q, st.volumeHistory); ok {
		results = append(results, r)
	}

	return results
}

func (d *Detector) checkPriceChange(q Quote, history []Quote) (Result, bool) {
	if len(history) < 2 {
		return Result{}, false
	}

	oldest := history[0]
	if oldest.Close <= 0 {
		return Result{}, false
	}

	changePct := (q.Close - oldest.Close) / oldest.Close * 100
	if math.Abs(changePct) <= d.priceThresholdPct {
		return Result{}, false
	}

	return Result{
		Ticker:         q.Ticker,
		TriggerType:    TriggerPriceChange,
		PriceChangePct: changePct,
		DetectedAt:     q.Timestamp,
		Critical:       math.Abs(changePct) > d.criticalPct,
	}, true
}

func (d *Detector) checkVolumeSpike(q Quote, history []Quote) (Result, bool) {
	baseline := history[:len(history)-1]
	if len(baseline) == 0 {
		return Result{}, false
	}

	var sum int64
	for _, v := range baseline {
		sum += v.Volume
	}
	avg := float64(sum) / float64(len(baseline))
	if avg <= 0 {
		return Result{}, false
	}

	ratio := float64(q.Volume) / avg
	if ratio <= d.volumeThreshold {
		return Result{}, false
	}

	return Result{
		Ticker:      q.Ticker,
		TriggerType: TriggerVolumeSpike,
		VolumeRatio: ratio,
		DetectedAt:  q.Timestamp,
	}, true
}

func evict(history []Quote, now time.Time, window time.Duration) []Quote {
	cutoff := now.Add(-window)
	i := 0
	for i < len(history) && history[i].Timestamp.Before(cutoff) {
		i++
	}
	return history[i:]
}

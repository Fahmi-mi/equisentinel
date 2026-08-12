package health

import (
	"encoding/json"
	"net/http"
)

type Status struct {
	NATSConnected bool `json:"nats_connected"`
	WSClients     int  `json:"ws_clients"`
}

type StatusFunc func() Status

func Handler(statusFn StatusFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		status := statusFn()

		w.Header().Set("Content-Type", "application/json")
		if !status.NATSConnected {
			w.WriteHeader(http.StatusServiceUnavailable)
		}
		json.NewEncoder(w).Encode(status)
	}
}

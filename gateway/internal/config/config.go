package config

import (
	"os"
	"strconv"
	"strings"
)

type Config struct {
	NATSURL                 string
	DatabaseURL             string
	HTTPPort                string
	PriceChangePctThreshold float64
	VolumeRatioThreshold    float64
	CriticalPriceChangePct  float64
	DebounceWindowSeconds   int
	AllowedOrigins          []string
}

func Load() Config {
	return Config{
		NATSURL:                 getEnv("NATS_URL", "nats://localhost:4222"),
		DatabaseURL:             getEnv("DATABASE_URL", "postgresql://equisentinel:equisentinel@localhost:5432/equisentinel"),
		HTTPPort:                getEnv("HTTP_PORT", "8080"),
		PriceChangePctThreshold: getEnvFloat("PRICE_CHANGE_THRESHOLD_PCT", 3.0),
		VolumeRatioThreshold:    getEnvFloat("VOLUME_RATIO_THRESHOLD", 5.0),
		CriticalPriceChangePct:  getEnvFloat("CRITICAL_PRICE_CHANGE_PCT", 5.0),
		DebounceWindowSeconds:   getEnvInt("DEBOUNCE_WINDOW_SECONDS", 30),
		AllowedOrigins:          strings.Split(getEnv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:4173"), ","),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvFloat(key string, fallback float64) float64 {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	parsed, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return fallback
	}
	return parsed
}

func getEnvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return parsed
}

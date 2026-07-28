from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent / "config"


@dataclass(frozen=True)
class TickerConfig:
    ticker: str
    base_price: float
    volatility: float  # per-tick log-return stddev
    drift: float  # per-tick log-return drift under normal conditions
    avg_volume: int  # average volume per candle


@dataclass(frozen=True)
class ScenarioConfig:
    ticker: str
    type: str  # "price_move" | "volume_spike"
    trigger_at_seconds: float
    duration_seconds: float
    magnitude_pct: Optional[float] = None
    volume_multiplier: Optional[float] = None
    news_headline: Optional[str] = None
    news_source: Optional[str] = None


@dataclass(frozen=True)
class SimulatorSettings:
    nats_url: str
    candle_interval_seconds: float
    ticks_per_candle: int
    random_seed: Optional[int]


def load_tickers(path: Optional[Path] = None) -> list[TickerConfig]:
    path = path or DEFAULT_CONFIG_DIR / "tickers.yaml"
    raw = yaml.safe_load(path.read_text())
    return [TickerConfig(**item) for item in raw["tickers"]]


def load_scenarios(path: Optional[Path] = None) -> list[ScenarioConfig]:
    path = path or DEFAULT_CONFIG_DIR / "scenarios.yaml"
    raw = yaml.safe_load(path.read_text()) or {}
    scenarios = []
    for item in raw.get("scenarios", []):
        item = dict(item)
        news = item.pop("news", None) or {}
        scenarios.append(
            ScenarioConfig(
                news_headline=news.get("headline"),
                news_source=news.get("source"),
                **item,
            )
        )
    return scenarios


def load_settings() -> SimulatorSettings:
    seed = os.getenv("SIM_RANDOM_SEED")
    return SimulatorSettings(
        nats_url=os.getenv("NATS_URL", "nats://localhost:4222"),
        candle_interval_seconds=float(os.getenv("CANDLE_INTERVAL_SECONDS", "2")),
        ticks_per_candle=int(os.getenv("TICKS_PER_CANDLE", "5")),
        random_seed=int(seed) if seed else None,
    )

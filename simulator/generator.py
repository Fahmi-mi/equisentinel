from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from config import TickerConfig


@dataclass
class Candle:
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class ScenarioOverride:
    """Overrides applied on top of a ticker's normal GBM parameters while a scenario is active."""

    drift_per_tick: Optional[float] = None
    volume_multiplier: float = 1.0


@dataclass
class TickerState:
    cfg: TickerConfig
    rng: np.random.Generator = field(default_factory=np.random.default_rng)
    last_price: float = field(init=False)

    def __post_init__(self) -> None:
        self.last_price = self.cfg.base_price


def _simulate_tick_price(state: TickerState, override: ScenarioOverride) -> float:
    drift = override.drift_per_tick if override.drift_per_tick is not None else state.cfg.drift
    vol = state.cfg.volatility
    shock = state.rng.normal()
    log_return = drift - 0.5 * vol**2 + vol * shock
    state.last_price = max(state.last_price * math.exp(log_return), 0.01)
    return state.last_price


def _simulate_tick_volume(state: TickerState, override: ScenarioOverride, ticks_per_candle: int) -> int:
    base = (state.cfg.avg_volume / ticks_per_candle) * override.volume_multiplier
    sampled = state.rng.lognormal(mean=math.log(max(base, 1.0)), sigma=0.3)
    return max(int(sampled), 0)


def generate_candle(
    state: TickerState,
    ticks_per_candle: int,
    override: Optional[ScenarioOverride] = None,
) -> Candle:
    override = override or ScenarioOverride()
    open_price = state.last_price
    prices: list[float] = []
    total_volume = 0
    for _ in range(ticks_per_candle):
        prices.append(_simulate_tick_price(state, override))
        total_volume += _simulate_tick_volume(state, override, ticks_per_candle)
    return Candle(
        ticker=state.cfg.ticker,
        open=open_price,
        high=max(open_price, *prices),
        low=min(open_price, *prices),
        close=prices[-1],
        volume=total_volume,
    )

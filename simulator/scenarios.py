from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import structlog

from config import ScenarioConfig, SimulatorSettings
from generator import ScenarioOverride

log = structlog.get_logger()


@dataclass
class _ActiveScenario:
    config: ScenarioConfig
    drift_per_tick: Optional[float]
    volume_multiplier: float
    ends_at: float


class ScenarioEngine:
    """Triggers scheduled scenarios per ticker at their configured offset and expires them
    once their duration elapses. Overrides are spread evenly across the remaining ticks in
    the scenario's window so the target magnitude is reached by the time it ends."""

    def __init__(self, scenarios: list[ScenarioConfig], settings: SimulatorSettings) -> None:
        self._settings = settings
        self._pending: dict[str, list[ScenarioConfig]] = {}
        for scenario in sorted(scenarios, key=lambda s: s.trigger_at_seconds):
            self._pending.setdefault(scenario.ticker, []).append(scenario)
        self._active: dict[str, _ActiveScenario] = {}

    def poll(self, ticker: str, elapsed_seconds: float) -> tuple[ScenarioOverride, Optional[ScenarioConfig]]:
        """Advance the schedule for `ticker` and return (override_to_apply, config_if_just_triggered)."""
        triggered = self._maybe_activate(ticker, elapsed_seconds)

        active = self._active.get(ticker)
        if active is not None and elapsed_seconds >= active.ends_at:
            log.info("scenario_ended", ticker=ticker, type=active.config.type)
            del self._active[ticker]
            active = None

        override = ScenarioOverride(
            drift_per_tick=active.drift_per_tick if active else None,
            volume_multiplier=active.volume_multiplier if active else 1.0,
        )
        return override, triggered

    def _maybe_activate(self, ticker: str, elapsed_seconds: float) -> Optional[ScenarioConfig]:
        queue = self._pending.get(ticker)
        if not queue or ticker in self._active:
            return None
        if queue[0].trigger_at_seconds > elapsed_seconds:
            return None

        config = queue.pop(0)
        self._active[ticker] = self._build_active(config, elapsed_seconds)
        log.info(
            "scenario_triggered",
            ticker=ticker,
            type=config.type,
            magnitude_pct=config.magnitude_pct,
            volume_multiplier=config.volume_multiplier,
        )
        return config

    def _build_active(self, config: ScenarioConfig, now: float) -> _ActiveScenario:
        remaining_candles = max(
            1, math.ceil(config.duration_seconds / self._settings.candle_interval_seconds)
        )
        total_ticks = remaining_candles * self._settings.ticks_per_candle

        drift_per_tick = None
        if config.type == "price_move" and config.magnitude_pct is not None:
            target_log_return = math.log(1 + config.magnitude_pct / 100)
            drift_per_tick = target_log_return / total_ticks

        return _ActiveScenario(
            config=config,
            drift_per_tick=drift_per_tick,
            volume_multiplier=config.volume_multiplier or 1.0,
            ends_at=now + config.duration_seconds,
        )

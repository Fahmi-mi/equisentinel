import numpy as np

from config import TickerConfig
from generator import ScenarioOverride, TickerState, generate_candle


def make_state(seed: int = 42, **overrides) -> TickerState:
    params = dict(ticker="TEST", base_price=1000.0, volatility=0.001, drift=0.0, avg_volume=100_000)
    params.update(overrides)
    return TickerState(cfg=TickerConfig(**params), rng=np.random.default_rng(seed))


def test_price_never_negative_under_extreme_volatility():
    state = make_state(volatility=5.0)
    for _ in range(200):
        candle = generate_candle(state, ticks_per_candle=5)
        assert candle.low > 0
        assert candle.close > 0


def test_ohlc_invariants_hold():
    state = make_state()
    for _ in range(50):
        candle = generate_candle(state, ticks_per_candle=10)
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        assert candle.volume >= 0


def test_open_price_carries_over_from_previous_close():
    state = make_state()
    first = generate_candle(state, ticks_per_candle=5)
    second = generate_candle(state, ticks_per_candle=5)
    assert second.open == first.close


def test_positive_drift_override_trends_price_up():
    state = make_state(volatility=0.0001)
    override = ScenarioOverride(drift_per_tick=0.05)
    candle = generate_candle(state, ticks_per_candle=20, override=override)
    assert candle.close > candle.open


def test_volume_multiplier_scales_volume():
    baseline = generate_candle(make_state(seed=1), ticks_per_candle=20)
    spiked = generate_candle(
        make_state(seed=1), ticks_per_candle=20, override=ScenarioOverride(volume_multiplier=10.0)
    )

    assert spiked.volume > baseline.volume * 5

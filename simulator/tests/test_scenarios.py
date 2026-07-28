import math

from config import ScenarioConfig, SimulatorSettings
from scenarios import ScenarioEngine


def make_settings() -> SimulatorSettings:
    return SimulatorSettings(
        nats_url="nats://localhost:4222",
        candle_interval_seconds=2.0,
        ticks_per_candle=5,
        random_seed=None,
    )


def test_scenario_not_active_before_trigger_time():
    settings = make_settings()
    scenario = ScenarioConfig(
        ticker="GOTO", type="price_move", trigger_at_seconds=30, duration_seconds=10, magnitude_pct=-7
    )
    engine = ScenarioEngine([scenario], settings)

    override, triggered = engine.poll("GOTO", elapsed_seconds=10)
    assert triggered is None
    assert override.drift_per_tick is None
    assert override.volume_multiplier == 1.0


def test_price_move_activates_and_expires():
    settings = make_settings()
    scenario = ScenarioConfig(
        ticker="GOTO", type="price_move", trigger_at_seconds=30, duration_seconds=10, magnitude_pct=-7
    )
    engine = ScenarioEngine([scenario], settings)

    override, triggered = engine.poll("GOTO", elapsed_seconds=30)
    assert triggered is scenario
    assert override.drift_per_tick is not None
    assert override.drift_per_tick < 0  # crash -> negative drift

    override, triggered = engine.poll("GOTO", elapsed_seconds=35)
    assert triggered is None
    assert override.drift_per_tick is not None  # still active mid-window

    override, triggered = engine.poll("GOTO", elapsed_seconds=41)
    assert triggered is None
    assert override.drift_per_tick is None  # expired


def test_price_move_drift_reaches_target_magnitude_over_window():
    settings = make_settings()
    scenario = ScenarioConfig(
        ticker="GOTO", type="price_move", trigger_at_seconds=0, duration_seconds=10, magnitude_pct=-7
    )
    engine = ScenarioEngine([scenario], settings)

    override, _ = engine.poll("GOTO", elapsed_seconds=0)
    total_ticks = math.ceil(10 / settings.candle_interval_seconds) * settings.ticks_per_candle
    expected_total_log_return = math.log(1 - 0.07)

    assert override.drift_per_tick * total_ticks == expected_total_log_return


def test_volume_spike_sets_multiplier_without_price_drift():
    settings = make_settings()
    scenario = ScenarioConfig(
        ticker="TLKM", type="volume_spike", trigger_at_seconds=5, duration_seconds=10, volume_multiplier=10
    )
    engine = ScenarioEngine([scenario], settings)

    override, triggered = engine.poll("TLKM", elapsed_seconds=5)
    assert triggered is scenario
    assert override.volume_multiplier == 10
    assert override.drift_per_tick is None


def test_second_scenario_only_activates_after_first_pending_is_reached():
    settings = make_settings()
    first = ScenarioConfig(
        ticker="GOTO", type="price_move", trigger_at_seconds=0, duration_seconds=5, magnitude_pct=-7
    )
    second = ScenarioConfig(
        ticker="GOTO", type="price_move", trigger_at_seconds=10, duration_seconds=5, magnitude_pct=3
    )
    engine = ScenarioEngine([first, second], settings)

    _, triggered_first = engine.poll("GOTO", elapsed_seconds=0)
    assert triggered_first is first

    # first scenario still active, second should not trigger even though its queue is next
    _, triggered_none = engine.poll("GOTO", elapsed_seconds=3)
    assert triggered_none is None

    # first expires at t=5, second triggers once elapsed reaches its own offset
    _, _ = engine.poll("GOTO", elapsed_seconds=6)
    _, triggered_second = engine.poll("GOTO", elapsed_seconds=10)
    assert triggered_second is second

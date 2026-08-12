from graph.nodes.technical_check import technical_check


def test_significant_data_passes_through():
    state = {
        "correlation_id": "x",
        "ticker": "GOTO",
        "trigger_type": "PRICE_CHANGE",
        "price_change_pct": -7.2,
        "volume_ratio": 0.0,
    }
    assert technical_check(state) == {}


def test_volume_spike_data_passes_through():
    state = {
        "correlation_id": "x",
        "ticker": "TLKM",
        "trigger_type": "VOLUME_SPIKE",
        "price_change_pct": 0.0,
        "volume_ratio": 10.0,
    }
    assert technical_check(state) == {}


def test_insignificant_data_short_circuits():
    state = {
        "correlation_id": "x",
        "ticker": "BBCA",
        "trigger_type": "PRICE_CHANGE",
        "price_change_pct": 0.0,
        "volume_ratio": 0.0,
    }
    result = technical_check(state)
    assert "analysis" in result
    assert result["analysis"].model_used == "none"
    assert result["analysis"].latency_ms == 0

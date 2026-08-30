import asyncio

from graph.nodes.technical_context import (
    NO_INDICATORS_CONTEXT,
    _format_indicators,
    make_technical_context_node,
)
from tests.fakes import FakePostgresStore

STATE = {
    "correlation_id": "x",
    "ticker": "GOTO",
    "trigger_type": "PRICE_CHANGE",
    "price_change_pct": -7.2,
    "volume_ratio": 0.0,
}


def _indicator_row(interval: str, rsi: float) -> dict:
    return {
        "ticker": "GOTO",
        "interval": interval,
        "timestamp": None,
        "sma": 100.5,
        "ema": 100.9,
        "rsi": rsi,
        "bollinger_upper": 105.0,
        "bollinger_middle": 100.5,
        "bollinger_lower": 96.0,
    }


def test_returns_formatted_indicators_when_available():
    postgres = FakePostgresStore(
        indicator_rows=[_indicator_row("5m", 55.0), _indicator_row("1m", 61.2)]
    )
    node = make_technical_context_node(postgres)

    result = asyncio.run(node(STATE))

    assert "1m" in result["technical_context"]
    assert "RSI" not in result["technical_context"]
    assert "rsi=61.2" in result["technical_context"]
    assert "sma=100.5" in result["technical_context"]
    assert "5m" in result["technical_context"]


def test_returns_default_when_no_indicators():
    postgres = FakePostgresStore(indicator_rows=[])
    node = make_technical_context_node(postgres)

    result = asyncio.run(node(STATE))

    assert result["technical_context"] == NO_INDICATORS_CONTEXT


def test_returns_default_when_query_errors():
    postgres = FakePostgresStore(exc=RuntimeError("connection refused"))
    node = make_technical_context_node(postgres)

    result = asyncio.run(node(STATE))

    assert result["technical_context"] == NO_INDICATORS_CONTEXT


def test_format_indicators_skips_null_values():
    row = _indicator_row("1m", 61.2)
    row["bollinger_upper"] = None
    row["bollinger_lower"] = None

    formatted = _format_indicators([row])

    assert "bollinger_upper" not in formatted
    assert "bollinger_middle=100.5" in formatted

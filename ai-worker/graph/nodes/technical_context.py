from __future__ import annotations

from typing import Awaitable, Callable

import structlog

from graph.state import AnalysisState
from storage.postgres import PostgresStore

log = structlog.get_logger()

NO_INDICATORS_CONTEXT = "Tidak ada data indikator teknikal."

_INDICATOR_FIELDS = (
    "sma",
    "ema",
    "rsi",
    "bollinger_upper",
    "bollinger_middle",
    "bollinger_lower",
)


def _format_indicators(rows: list[dict]) -> str:
    parts = []
    for row in sorted(rows, key=lambda r: r["interval"]):
        values = [f"{field}={row[field]:.1f}" for field in _INDICATOR_FIELDS if row.get(field) is not None]
        if values:
            parts.append(f"{row['interval']}: " + ", ".join(values))
    return " | ".join(parts)


def make_technical_context_node(
    postgres: PostgresStore,
) -> Callable[[AnalysisState], Awaitable[dict]]:
    async def technical_context(state: AnalysisState) -> dict:
        try:
            rows = await postgres.fetch_recent_indicators(state["ticker"])
        except Exception:
            log.warning("technical_indicators_fetch_failed", ticker=state["ticker"], exc_info=True)
            rows = []
        if not rows:
            return {"technical_context": NO_INDICATORS_CONTEXT}
        return {"technical_context": _format_indicators(rows)}

    return technical_context

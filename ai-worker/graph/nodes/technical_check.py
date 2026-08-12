from __future__ import annotations

from graph.state import AnalysisState
from schemas import AIAnalysis, RiskLevel, Sentiment

DEFAULT_SUMMARY = "Data tidak cukup untuk analisis, pantau secara manual."


def technical_check(state: AnalysisState) -> dict:
    if state["price_change_pct"] == 0 and state["volume_ratio"] == 0:
        return {
            "analysis": AIAnalysis(
                correlation_id=state["correlation_id"],
                ticker=state["ticker"],
                summary=DEFAULT_SUMMARY,
                sentiment=Sentiment.NEUTRAL,
                risk_level=RiskLevel.LOW,
                model_used="none",
                latency_ms=0,
            )
        }
    return {}

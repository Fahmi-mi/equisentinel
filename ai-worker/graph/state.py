from __future__ import annotations

from typing import NotRequired, TypedDict

from schemas import AIAnalysis


class AnalysisState(TypedDict):
    correlation_id: str
    ticker: str
    trigger_type: str
    price_change_pct: float
    volume_ratio: float
    news_context: NotRequired[str]
    analysis: NotRequired[AIAnalysis]

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class Sentiment(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AIAnalysis(BaseModel):
    correlation_id: str
    ticker: str
    summary: str
    sentiment: Sentiment
    risk_level: RiskLevel
    model_used: str
    latency_ms: int

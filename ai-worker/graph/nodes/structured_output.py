from __future__ import annotations

from typing import Awaitable, Callable

from nats.js import JetStreamContext

from graph.state import AnalysisState
from proto_gen import ai_analysis_pb2
from schemas import RiskLevel, Sentiment

RESULTS_SUBJECT = "stock.results"

_SENTIMENT_TO_PROTO = {
    Sentiment.BULLISH: ai_analysis_pb2.SENTIMENT_BULLISH,
    Sentiment.BEARISH: ai_analysis_pb2.SENTIMENT_BEARISH,
    Sentiment.NEUTRAL: ai_analysis_pb2.SENTIMENT_NEUTRAL,
}

_RISK_LEVEL_TO_PROTO = {
    RiskLevel.LOW: ai_analysis_pb2.RISK_LEVEL_LOW,
    RiskLevel.MEDIUM: ai_analysis_pb2.RISK_LEVEL_MEDIUM,
    RiskLevel.HIGH: ai_analysis_pb2.RISK_LEVEL_HIGH,
}


def make_structured_output_node(js: JetStreamContext) -> Callable[[AnalysisState], Awaitable[dict]]:
    async def structured_output(state: AnalysisState) -> dict:
        analysis = state["analysis"]

        message = ai_analysis_pb2.AiAnalysis(
            correlation_id=analysis.correlation_id,
            ticker=analysis.ticker,
            summary=analysis.summary,
            sentiment=_SENTIMENT_TO_PROTO[analysis.sentiment],
            risk_level=_RISK_LEVEL_TO_PROTO[analysis.risk_level],
            model_used=analysis.model_used,
            latency_ms=analysis.latency_ms,
        )
        await js.publish(RESULTS_SUBJECT, message.SerializeToString())
        return {}

    return structured_output

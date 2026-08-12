from __future__ import annotations

import time
from typing import Awaitable, Callable

import structlog
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from graph.state import AnalysisState
from schemas import AIAnalysis, RiskLevel, Sentiment
from storage.cache import SentimentCache

log = structlog.get_logger()

DEFAULT_SUMMARY = "Data tidak cukup untuk analisis, pantau secara manual."

PROMPT_TEMPLATE = (
    "Saham {ticker} bergerak {price_change_pct}% dengan rasio volume {volume_ratio}x "
    "dibanding rata-rata. Berita terkait:\n{news_context}\n\n"
    "Analisis sentimen dan berikan risk level (LOW/MEDIUM/HIGH) beserta alasan singkat."
)


class _Verdict(BaseModel):
    summary: str
    sentiment: Sentiment
    risk_level: RiskLevel


def make_llm_reasoning_node(
    client: ChatOpenAI,
    cache: SentimentCache,
    model_name: str,
    on_call_result: Callable[[bool], None] | None = None,
) -> Callable[[AnalysisState], Awaitable[dict]]:
    structured_client = client.with_structured_output(_Verdict, method="function_calling")

    async def llm_reasoning(state: AnalysisState) -> dict:
        try:
            cached = await cache.get(state["ticker"])
        except Exception:
            log.warning("sentiment_cache_read_failed", ticker=state["ticker"], exc_info=True)
            cached = None

        if cached is not None:
            verdict = _Verdict.model_validate_json(cached)
            log.info("sentiment_cache_hit", ticker=state["ticker"])
            return {
                "analysis": AIAnalysis(
                    correlation_id=state["correlation_id"],
                    ticker=state["ticker"],
                    summary=verdict.summary,
                    sentiment=verdict.sentiment,
                    risk_level=verdict.risk_level,
                    model_used=model_name,
                    latency_ms=0,
                )
            }

        prompt = PROMPT_TEMPLATE.format(
            ticker=state["ticker"],
            price_change_pct=state["price_change_pct"],
            volume_ratio=state["volume_ratio"],
            news_context=state.get("news_context", "Tidak ada berita."),
        )

        start = time.monotonic()
        try:
            verdict: _Verdict = await structured_client.ainvoke(prompt)
        except Exception:
            log.warning("deepseek_call_failed", ticker=state["ticker"], exc_info=True)
            if on_call_result is not None:
                on_call_result(False)
            return {
                "analysis": AIAnalysis(
                    correlation_id=state["correlation_id"],
                    ticker=state["ticker"],
                    summary=DEFAULT_SUMMARY,
                    sentiment=Sentiment.NEUTRAL,
                    risk_level=RiskLevel.LOW,
                    model_used=model_name,
                    latency_ms=int((time.monotonic() - start) * 1000),
                )
            }
        latency_ms = int((time.monotonic() - start) * 1000)
        if on_call_result is not None:
            on_call_result(True)

        try:
            await cache.set(state["ticker"], verdict.model_dump_json())
        except Exception:
            log.warning("sentiment_cache_write_failed", ticker=state["ticker"], exc_info=True)

        return {
            "analysis": AIAnalysis(
                correlation_id=state["correlation_id"],
                ticker=state["ticker"],
                summary=verdict.summary,
                sentiment=verdict.sentiment,
                risk_level=verdict.risk_level,
                model_used=model_name,
                latency_ms=latency_ms,
            )
        }

    return llm_reasoning

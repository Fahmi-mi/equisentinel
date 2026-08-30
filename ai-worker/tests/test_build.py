import asyncio

from graph.build import build_graph
from graph.nodes.llm_reasoning import _Verdict
from graph.nodes.technical_context import NO_INDICATORS_CONTEXT
from proto_gen import ai_analysis_pb2
from schemas import RiskLevel, Sentiment
from tests.fakes import (
    FakeCache,
    FakeChatClient,
    FakeJetStream,
    FakePostgresStore,
    FakePullSubscription,
    FakeStructuredClient,
)


def test_insignificant_anomaly_skips_pipeline():
    postgres = FakePostgresStore()
    js = FakeJetStream()
    verdict = _Verdict(summary="tidak dipakai", sentiment=Sentiment.NEUTRAL, risk_level=RiskLevel.LOW)
    llm_client = FakeChatClient(FakeStructuredClient(result=verdict))
    cache = FakeCache()

    graph = build_graph(postgres, js, llm_client, cache, "deepseek-chat")

    result = asyncio.run(
        graph.ainvoke(
            {
                "correlation_id": "x",
                "ticker": "BBCA",
                "trigger_type": "PRICE_CHANGE",
                "price_change_pct": 0.0,
                "volume_ratio": 0.0,
            }
        )
    )

    assert "news_context" not in result
    assert result["analysis"].model_used == "none"
    assert js.published == []


def test_significant_anomaly_runs_full_pipeline():
    postgres = FakePostgresStore(rows=[{"headline": "GOTO Anjlok Tajam"}])
    js = FakeJetStream()
    verdict = _Verdict(summary="Sentimen negatif", sentiment=Sentiment.BEARISH, risk_level=RiskLevel.HIGH)
    llm_client = FakeChatClient(FakeStructuredClient(result=verdict))
    cache = FakeCache()

    graph = build_graph(postgres, js, llm_client, cache, "deepseek-chat")

    result = asyncio.run(
        graph.ainvoke(
            {
                "correlation_id": "corr-1",
                "ticker": "GOTO",
                "trigger_type": "PRICE_CHANGE",
                "price_change_pct": -7.2,
                "volume_ratio": 0.0,
            }
        )
    )

    assert result["news_context"] == "- GOTO Anjlok Tajam"
    assert result["technical_context"] == NO_INDICATORS_CONTEXT
    assert result["analysis"].summary == "Sentimen negatif"
    assert len(js.published) == 1

    parsed = ai_analysis_pb2.AiAnalysis()
    parsed.ParseFromString(js.published[0][1])
    assert parsed.ticker == "GOTO"
    assert parsed.sentiment == ai_analysis_pb2.SENTIMENT_BEARISH


def test_volume_spike_anomaly_runs_full_pipeline():
    postgres = FakePostgresStore(rows=[])
    js = FakeJetStream(pull_subscription=FakePullSubscription(messages=[]))
    verdict = _Verdict(summary="Volume melonjak", sentiment=Sentiment.NEUTRAL, risk_level=RiskLevel.MEDIUM)
    llm_client = FakeChatClient(FakeStructuredClient(result=verdict))
    cache = FakeCache()

    graph = build_graph(postgres, js, llm_client, cache, "deepseek-chat")

    result = asyncio.run(
        graph.ainvoke(
            {
                "correlation_id": "corr-2",
                "ticker": "TLKM",
                "trigger_type": "VOLUME_SPIKE",
                "price_change_pct": 0.0,
                "volume_ratio": 10.0,
            }
        )
    )

    assert result["analysis"].summary == "Volume melonjak"
    assert len(js.published) == 1

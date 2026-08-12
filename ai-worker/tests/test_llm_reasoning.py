import asyncio

from graph.nodes.llm_reasoning import DEFAULT_SUMMARY, _Verdict, make_llm_reasoning_node
from schemas import RiskLevel, Sentiment
from tests.fakes import FakeCache, FakeChatClient, FakeStructuredClient

STATE = {
    "correlation_id": "x",
    "ticker": "GOTO",
    "trigger_type": "PRICE_CHANGE",
    "price_change_pct": -7.2,
    "volume_ratio": 0.0,
    "news_context": "- GOTO Anjlok Tajam",
}


def test_cache_hit_skips_llm_call():
    cached_verdict = _Verdict(summary="dari cache", sentiment=Sentiment.BEARISH, risk_level=RiskLevel.HIGH)
    cache = FakeCache(seed={"GOTO": cached_verdict.model_dump_json()})
    structured = FakeStructuredClient()
    node = make_llm_reasoning_node(FakeChatClient(structured), cache, "deepseek-chat")

    result = asyncio.run(node(STATE))
    assert structured.call_count == 0
    assert result["analysis"].summary == "dari cache"
    assert result["analysis"].latency_ms == 0


def test_cache_miss_calls_llm_and_caches_result():
    verdict = _Verdict(summary="hasil baru", sentiment=Sentiment.BULLISH, risk_level=RiskLevel.LOW)
    structured = FakeStructuredClient(result=verdict)
    cache = FakeCache()
    results: list[bool] = []
    node = make_llm_reasoning_node(
        FakeChatClient(structured), cache, "deepseek-chat", on_call_result=results.append
    )

    result = asyncio.run(node(STATE))
    assert structured.call_count == 1
    assert result["analysis"].summary == "hasil baru"
    assert cache._store["GOTO"] == verdict.model_dump_json()
    assert results == [True]


def test_llm_failure_falls_back_to_default():
    structured = FakeStructuredClient(exc=RuntimeError("timeout"))
    cache = FakeCache()
    results: list[bool] = []
    node = make_llm_reasoning_node(
        FakeChatClient(structured), cache, "deepseek-chat", on_call_result=results.append
    )

    result = asyncio.run(node(STATE))
    assert result["analysis"].summary == DEFAULT_SUMMARY
    assert result["analysis"].sentiment == Sentiment.NEUTRAL
    assert "GOTO" not in cache._store
    assert results == [False]


def test_cache_read_failure_still_calls_llm():
    verdict = _Verdict(summary="hasil baru", sentiment=Sentiment.BULLISH, risk_level=RiskLevel.LOW)
    structured = FakeStructuredClient(result=verdict)
    cache = FakeCache(exc=ConnectionError("redis down"))
    node = make_llm_reasoning_node(FakeChatClient(structured), cache, "deepseek-chat")

    result = asyncio.run(node(STATE))
    assert structured.call_count == 1
    assert result["analysis"].summary == "hasil baru"

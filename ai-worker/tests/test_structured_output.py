import asyncio

from graph.nodes.structured_output import RESULTS_SUBJECT, make_structured_output_node
from proto_gen import ai_analysis_pb2
from schemas import AIAnalysis, RiskLevel, Sentiment
from tests.fakes import FakeJetStream


def test_publishes_correct_protobuf_message():
    js = FakeJetStream()
    node = make_structured_output_node(js)
    state = {
        "analysis": AIAnalysis(
            correlation_id="corr-1",
            ticker="GOTO",
            summary="Sentimen negatif.",
            sentiment=Sentiment.BEARISH,
            risk_level=RiskLevel.HIGH,
            model_used="deepseek-chat",
            latency_ms=1234,
        )
    }

    result = asyncio.run(node(state))
    assert result == {}
    assert len(js.published) == 1

    subject, data = js.published[0]
    assert subject == RESULTS_SUBJECT

    parsed = ai_analysis_pb2.AiAnalysis()
    parsed.ParseFromString(data)
    assert parsed.correlation_id == "corr-1"
    assert parsed.sentiment == ai_analysis_pb2.SENTIMENT_BEARISH
    assert parsed.risk_level == ai_analysis_pb2.RISK_LEVEL_HIGH
    assert parsed.latency_ms == 1234

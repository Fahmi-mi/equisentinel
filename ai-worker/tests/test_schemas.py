import json

from schemas import AIAnalysis, RiskLevel, Sentiment


def test_ai_analysis_round_trip():
    analysis = AIAnalysis(
        correlation_id="corr-1",
        ticker="GOTO",
        summary="Sentimen negatif akibat divestasi.",
        sentiment=Sentiment.BEARISH,
        risk_level=RiskLevel.HIGH,
        model_used="deepseek-chat",
        latency_ms=1234,
    )
    parsed = json.loads(analysis.model_dump_json())
    assert parsed["sentiment"] == "BEARISH"
    assert parsed["risk_level"] == "HIGH"
    assert parsed["latency_ms"] == 1234


def test_ai_analysis_rejects_invalid_sentiment():
    try:
        AIAnalysis(
            correlation_id="corr-1",
            ticker="GOTO",
            summary="x",
            sentiment="NOT_A_SENTIMENT",
            risk_level=RiskLevel.LOW,
            model_used="deepseek-chat",
            latency_ms=0,
        )
    except ValueError:
        return
    raise AssertionError("expected ValueError for invalid sentiment")

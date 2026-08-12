import asyncio

from graph.nodes.context_retrieval import NO_NEWS_CONTEXT, make_context_retrieval_node
from proto_gen import news_article_pb2
from tests.fakes import FakeJetStream, FakeMsg, FakePostgresStore, FakePullSubscription

STATE = {
    "correlation_id": "x",
    "ticker": "GOTO",
    "trigger_type": "PRICE_CHANGE",
    "price_change_pct": -7.2,
    "volume_ratio": 0.0,
}


def _news_msg(headline: str) -> FakeMsg:
    article = news_article_pb2.NewsArticle(ticker="GOTO", headline=headline, body="x", source="Wire")
    return FakeMsg(article.SerializeToString())


def test_uses_postgres_when_available():
    postgres = FakePostgresStore(rows=[{"headline": "Berita dari Postgres"}])
    js = FakeJetStream()
    node = make_context_retrieval_node(postgres, js)

    result = asyncio.run(node(STATE))
    assert result["news_context"] == "- Berita dari Postgres"


def test_falls_back_to_nats_when_postgres_empty():
    postgres = FakePostgresStore(rows=[])
    js = FakeJetStream(pull_subscription=FakePullSubscription(messages=[_news_msg("Berita dari NATS")]))
    node = make_context_retrieval_node(postgres, js)

    result = asyncio.run(node(STATE))
    assert result["news_context"] == "- Berita dari NATS"


def test_falls_back_to_nats_when_postgres_errors():
    postgres = FakePostgresStore(exc=RuntimeError("connection refused"))
    js = FakeJetStream(pull_subscription=FakePullSubscription(messages=[_news_msg("Berita dari NATS")]))
    node = make_context_retrieval_node(postgres, js)

    result = asyncio.run(node(STATE))
    assert result["news_context"] == "- Berita dari NATS"


def test_returns_default_when_both_sources_empty():
    postgres = FakePostgresStore(rows=[])
    js = FakeJetStream(pull_subscription=FakePullSubscription(messages=[]))
    node = make_context_retrieval_node(postgres, js)

    result = asyncio.run(node(STATE))
    assert result["news_context"] == NO_NEWS_CONTEXT


def test_returns_default_when_nats_stream_missing():
    postgres = FakePostgresStore(rows=[])
    js = FakeJetStream(pull_subscription=FakePullSubscription(exc=RuntimeError("stream not found")))
    node = make_context_retrieval_node(postgres, js)

    result = asyncio.run(node(STATE))
    assert result["news_context"] == NO_NEWS_CONTEXT

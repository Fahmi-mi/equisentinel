from __future__ import annotations

import datetime
from typing import Awaitable, Callable

import nats.errors
import structlog
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, DeliverPolicy

from graph.state import AnalysisState
from proto_gen import news_article_pb2
from storage.postgres import PostgresStore

log = structlog.get_logger()

WINDOW_MINUTES = 30
NO_NEWS_CONTEXT = "Tidak ada berita terkait dalam 30 menit terakhir."


def make_context_retrieval_node(
    postgres: PostgresStore, js: JetStreamContext
) -> Callable[[AnalysisState], Awaitable[dict]]:
    async def context_retrieval(state: AnalysisState) -> dict:
        try:
            news = await postgres.fetch_recent_news(state["ticker"], window_minutes=WINDOW_MINUTES)
            headlines = [item["headline"] for item in news]
        except Exception:
            log.warning("postgres_news_query_failed", ticker=state["ticker"], exc_info=True)
            headlines = []

        if not headlines:
            headlines = await _fetch_from_nats(js, state["ticker"])

        if not headlines:
            return {"news_context": NO_NEWS_CONTEXT}
        return {"news_context": "\n".join(f"- {h}" for h in headlines)}

    return context_retrieval


async def _fetch_from_nats(js: JetStreamContext, ticker: str) -> list[str]:
    start_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=WINDOW_MINUTES)
    try:
        sub = await js.pull_subscribe(
            f"stock.news.{ticker}",
            config=ConsumerConfig(deliver_policy=DeliverPolicy.BY_START_TIME, opt_start_time=start_time),
        )
        msgs = await sub.fetch(batch=20, timeout=2)
    except nats.errors.TimeoutError:
        return []
    except Exception:
        log.warning("nats_news_fetch_failed", ticker=ticker, exc_info=True)
        return []

    headlines = []
    for msg in msgs:
        article = news_article_pb2.NewsArticle()
        article.ParseFromString(msg.data)
        headlines.append(article.headline)
        await msg.ack()
    return headlines

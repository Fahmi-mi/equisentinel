from __future__ import annotations

import uuid
from typing import Optional

import structlog
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.js.errors import NotFoundError

from config import SimulatorSettings
from generator import Candle
from proto_gen import news_article_pb2, stock_quote_pb2

log = structlog.get_logger()

QUOTES_STREAM = "STOCK_QUOTES"
QUOTES_SUBJECT_PREFIX = "stock.quotes"
NEWS_STREAM = "STOCK_NEWS"
NEWS_SUBJECT_PREFIX = "stock.news"
STREAM_MAX_AGE_SECONDS = 24 * 60 * 60


class Publisher:
    def __init__(self, settings: SimulatorSettings) -> None:
        self._settings = settings
        self._nc: Optional[NATS] = None
        self._js: Optional[JetStreamContext] = None

    async def connect(self) -> None:
        self._nc = NATS()
        await self._nc.connect(servers=[self._settings.nats_url])
        self._js = self._nc.jetstream()
        await self._ensure_stream(QUOTES_STREAM, f"{QUOTES_SUBJECT_PREFIX}.*")
        await self._ensure_stream(NEWS_STREAM, f"{NEWS_SUBJECT_PREFIX}.*")
        log.info("nats_connected", url=self._settings.nats_url)

    async def _ensure_stream(self, name: str, subject: str) -> None:
        try:
            await self._js.stream_info(name)
            log.debug("stream_already_exists", name=name)
        except NotFoundError:
            await self._js.add_stream(
                name=name, subjects=[subject], max_age=STREAM_MAX_AGE_SECONDS
            )

    async def close(self) -> None:
        if self._nc is None:
            return
        try:
            await self._nc.drain()
        except Exception:
            log.warning("nats_drain_failed", exc_info=True)
            await self._nc.close()

    @property
    def is_connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def publish_candle(self, candle: Candle) -> None:
        msg = stock_quote_pb2.StockQuote(
            ticker=candle.ticker,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )
        msg.timestamp.GetCurrentTime()
        subject = f"{QUOTES_SUBJECT_PREFIX}.{candle.ticker}"
        await self._js.publish(subject, msg.SerializeToString())

    async def publish_news(self, ticker: str, headline: str, source: str) -> None:
        msg = news_article_pb2.NewsArticle(
            id=str(uuid.uuid4()),
            ticker=ticker,
            headline=headline,
            body=headline,
            source=source,
        )
        msg.published_at.GetCurrentTime()
        subject = f"{NEWS_SUBJECT_PREFIX}.{ticker}"
        await self._js.publish(subject, msg.SerializeToString())
        log.info("news_published", ticker=ticker, headline=headline)

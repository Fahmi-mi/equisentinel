from __future__ import annotations

import redis.asyncio as redis


class SentimentCache:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.from_url(redis_url, decode_responses=True)

    async def connect(self) -> None:
        await self._client.ping()

    async def close(self) -> None:
        await self._client.aclose()

    async def get(self, ticker: str) -> str | None:
        return await self._client.get(f"sentiment:{ticker}")

    async def set(self, ticker: str, analysis_json: str, ttl_seconds: int = 300) -> None:
        await self._client.set(f"sentiment:{ticker}", analysis_json, ex=ttl_seconds)

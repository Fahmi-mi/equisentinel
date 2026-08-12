from __future__ import annotations

import asyncpg


class PostgresStore:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(self._database_url)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()

    async def fetch_recent_news(self, ticker: str, window_minutes: int = 30) -> list[dict]:
        assert self._pool is not None
        rows = await self._pool.fetch(
            """
            SELECT headline, body, source, published_at
            FROM news_articles
            WHERE ticker = $1 AND published_at >= now() - make_interval(mins => $2)
            ORDER BY published_at DESC
            """,
            ticker,
            window_minutes,
        )
        return [dict(row) for row in rows]

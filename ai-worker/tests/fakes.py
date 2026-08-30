from __future__ import annotations

import nats.errors


class FakePostgresStore:
    def __init__(
        self,
        rows: list[dict] | None = None,
        exc: Exception | None = None,
        indicator_rows: list[dict] | None = None,
    ) -> None:
        self._rows = rows or []
        self._indicator_rows = indicator_rows or []
        self._exc = exc

    async def fetch_recent_news(self, ticker: str, window_minutes: int = 30) -> list[dict]:
        if self._exc is not None:
            raise self._exc
        return self._rows

    async def fetch_recent_indicators(self, ticker: str) -> list[dict]:
        if self._exc is not None:
            raise self._exc
        return self._indicator_rows


class FakePullSubscription:
    def __init__(self, messages: list | None = None, exc: Exception | None = None) -> None:
        self._messages = messages or []
        self._exc = exc

    async def fetch(self, batch: int = 1, timeout: float | None = None) -> list:
        if self._exc is not None:
            raise self._exc
        if not self._messages:
            raise nats.errors.TimeoutError
        return self._messages


class FakeMsg:
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def ack(self) -> None:
        pass


class FakeJetStream:
    def __init__(self, pull_subscription: FakePullSubscription | None = None) -> None:
        self._pull_subscription = pull_subscription or FakePullSubscription()
        self.published: list[tuple[str, bytes]] = []

    async def pull_subscribe(self, subject: str, **kwargs) -> FakePullSubscription:
        return self._pull_subscription

    async def publish(self, subject: str, data: bytes) -> None:
        self.published.append((subject, data))


class FakeStructuredClient:
    def __init__(self, result=None, exc: Exception | None = None) -> None:
        self._result = result
        self._exc = exc
        self.call_count = 0

    async def ainvoke(self, prompt: str):
        self.call_count += 1
        if self._exc is not None:
            raise self._exc
        return self._result


class FakeChatClient:
    def __init__(self, structured_client: FakeStructuredClient) -> None:
        self._structured_client = structured_client

    def with_structured_output(self, model, method: str | None = None):
        return self._structured_client


class FakeCache:
    def __init__(self, seed: dict[str, str] | None = None, exc: Exception | None = None) -> None:
        self._store = dict(seed or {})
        self._exc = exc

    async def get(self, ticker: str) -> str | None:
        if self._exc is not None:
            raise self._exc
        return self._store.get(ticker)

    async def set(self, ticker: str, value: str, ttl_seconds: int = 300) -> None:
        if self._exc is not None:
            raise self._exc
        self._store[ticker] = value

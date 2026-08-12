from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Awaitable, Callable

from aiohttp import web


@dataclass
class Status:
    nats_connected: bool


StatusFunc = Callable[[], Status]


def make_health_handler(status_fn: StatusFunc) -> Callable[[web.Request], Awaitable[web.Response]]:
    async def handler(request: web.Request) -> web.Response:
        status = status_fn()
        http_status = 200 if status.nats_connected else 503
        return web.json_response(asdict(status), status=http_status)

    return handler

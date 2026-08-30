from __future__ import annotations

import asyncio
import signal

import structlog
from aiohttp import web
from sqlalchemy import Engine, text

from etl.config import load_settings
from etl.health import Status, make_health_handler
from etl.storage.warehouse_db import WarehouseDB

log = structlog.get_logger()


def _engine_connected(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _db_status(db: WarehouseDB) -> Status:
    return Status(
        source_db_connected=_engine_connected(db.source_engine),
        warehouse_connected=_engine_connected(db.warehouse_engine),
    )


async def main() -> None:
    settings = load_settings()
    db = WarehouseDB(settings)

    app = web.Application()
    app.router.add_get("/health", make_health_handler(lambda: _db_status(db)))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(settings.http_port))
    await site.start()
    log.info("etl_health_server_starting", port=settings.http_port)

    proc = await asyncio.create_subprocess_exec("airflow", "standalone")

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    log.info("shutting_down")
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=10)
    except asyncio.TimeoutError:
        proc.kill()
    await runner.cleanup()
    db.dispose()


if __name__ == "__main__":
    asyncio.run(main())

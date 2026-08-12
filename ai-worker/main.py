from __future__ import annotations

import asyncio
import signal

import structlog
from aiohttp import web
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

from config import load_settings
from graph.build import build_graph
from health import Status, make_health_handler
from llm.deepseek_client import build_deepseek_client
from proto_gen import anomaly_event_pb2
from storage.cache import SentimentCache
from storage.postgres import PostgresStore

log = structlog.get_logger()

ANOMALY_STREAM = "STOCK_ANOMALY"
ANOMALY_SUBJECT = "stock.anomaly"
ANOMALY_CRITICAL_SUBJECT = "stock.anomaly.critical"
ANOMALY_DURABLE = "ai-worker-anomaly"
ANOMALY_CRITICAL_DURABLE = "ai-worker-anomaly-critical"
RESULTS_STREAM = "STOCK_RESULTS"
RESULTS_SUBJECT = "stock.results"
QUEUE_DEPTH_POLL_SECONDS = 10


async def main() -> None:
    settings = load_settings()

    nc = NATS()
    await nc.connect(servers=[settings.nats_url])
    js = nc.jetstream()

    try:
        await js.stream_info(RESULTS_STREAM)
    except Exception:
        await js.add_stream(name=RESULTS_STREAM, subjects=[RESULTS_SUBJECT])

    postgres = PostgresStore(settings.database_url)
    await postgres.connect()
    cache = SentimentCache(settings.redis_url)
    await cache.connect()
    llm_client = build_deepseek_client(settings.deepseek_api_key, settings.deepseek_model)

    deepseek_reachable = True
    queue_depth = 0

    def track_llm_result(success: bool) -> None:
        nonlocal deepseek_reachable
        deepseek_reachable = success

    graph = build_graph(postgres, js, llm_client, cache, settings.deepseek_model, track_llm_result)

    async def handle_anomaly(msg: Msg) -> None:
        event = anomaly_event_pb2.AnomalyEvent()
        event.ParseFromString(msg.data)
        log.info("anomaly_received", ticker=event.ticker, trigger_type=event.trigger_type)

        state = {
            "correlation_id": event.correlation_id,
            "ticker": event.ticker,
            "trigger_type": event.trigger_type,
            "price_change_pct": event.price_change_pct,
            "volume_ratio": event.volume_ratio,
        }
        try:
            await graph.ainvoke(state)
        except Exception:
            log.error("anomaly_processing_failed", ticker=event.ticker, exc_info=True)
        finally:
            await msg.ack()

    await js.subscribe(ANOMALY_SUBJECT, durable=ANOMALY_DURABLE, cb=handle_anomaly, manual_ack=True)
    await js.subscribe(
        ANOMALY_CRITICAL_SUBJECT, durable=ANOMALY_CRITICAL_DURABLE, cb=handle_anomaly, manual_ack=True
    )

    async def poll_queue_depth() -> None:
        nonlocal queue_depth
        while True:
            total = 0
            for durable in (ANOMALY_DURABLE, ANOMALY_CRITICAL_DURABLE):
                try:
                    info = await js.consumer_info(ANOMALY_STREAM, durable)
                    total += info.num_pending
                except Exception:
                    pass
            queue_depth = total
            await asyncio.sleep(QUEUE_DEPTH_POLL_SECONDS)

    poller_task = asyncio.create_task(poll_queue_depth())

    def get_status() -> Status:
        return Status(
            nats_connected=nc.is_connected,
            deepseek_reachable=deepseek_reachable,
            queue_depth=queue_depth,
        )

    app = web.Application()
    app.router.add_get("/health", make_health_handler(get_status))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(settings.http_port))
    await site.start()
    log.info("http_server_starting", port=settings.http_port)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()

    log.info("shutting_down")
    poller_task.cancel()
    await runner.cleanup()
    await cache.close()
    await postgres.close()
    await nc.drain()


if __name__ == "__main__":
    asyncio.run(main())

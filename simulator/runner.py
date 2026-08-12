from __future__ import annotations

import asyncio
import signal
import time

import numpy as np
import structlog
from aiohttp import web
from dotenv import load_dotenv

from config import load_scenarios, load_settings, load_tickers
from generator import TickerState, generate_candle
from health import Status, make_health_handler
from publisher import Publisher
from scenarios import ScenarioEngine

log = structlog.get_logger()


async def _run_ticker(
    state: TickerState,
    settings,
    scenario_engine: ScenarioEngine,
    publisher: Publisher,
    clock_start: float,
) -> None:
    while True:
        await asyncio.sleep(settings.candle_interval_seconds)
        elapsed = time.monotonic() - clock_start

        override, triggered = scenario_engine.poll(state.cfg.ticker, elapsed)
        if triggered is not None and triggered.news_headline:
            await publisher.publish_news(
                ticker=state.cfg.ticker,
                headline=triggered.news_headline,
                source=triggered.news_source or "Simulated Wire",
            )

        candle = generate_candle(state, settings.ticks_per_candle, override)
        await publisher.publish_candle(candle)
        log.debug(
            "candle_published",
            ticker=candle.ticker,
            close=round(candle.close, 2),
            volume=candle.volume,
        )


async def run() -> None:
    load_dotenv()
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))  # INFO

    settings = load_settings()
    tickers = load_tickers()
    scenarios = load_scenarios()

    seed_seq = np.random.SeedSequence(settings.random_seed)
    child_seeds = seed_seq.spawn(len(tickers))

    scenario_engine = ScenarioEngine(scenarios, settings)
    publisher = Publisher(settings)
    await publisher.connect()

    app = web.Application()
    app.router.add_get("/health", make_health_handler(lambda: Status(nats_connected=publisher.is_connected)))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(settings.http_port))
    await site.start()
    log.info("http_server_starting", port=settings.http_port)

    states = [
        TickerState(cfg=cfg, rng=np.random.default_rng(seed))
        for cfg, seed in zip(tickers, child_seeds)
    ]

    clock_start = time.monotonic()
    log.info("simulator_started", tickers=[s.cfg.ticker for s in states], scenarios=len(scenarios))

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    ticker_tasks = [
        asyncio.create_task(_run_ticker(state, settings, scenario_engine, publisher, clock_start))
        for state in states
    ]
    stop_task = asyncio.create_task(stop_event.wait())

    try:
        await asyncio.wait([*ticker_tasks, stop_task], return_when=asyncio.FIRST_COMPLETED)
    finally:
        log.info("shutting_down")
        stop_task.cancel()
        for task in ticker_tasks:
            task.cancel()
        await asyncio.gather(*ticker_tasks, stop_task, return_exceptions=True)
        await runner.cleanup()
        await publisher.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

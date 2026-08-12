from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg
from nats.aio.client import Client as NATS

from proto_gen import ai_analysis_pb2, anomaly_event_pb2

NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://equisentinel:equisentinel@localhost:5432/equisentinel"
)
TIMEOUT_SECONDS = 30


async def main() -> int:
    correlation_id = str(uuid.uuid4())
    ticker = "TESTX"

    nc = NATS()
    await nc.connect(servers=[NATS_URL])
    js = nc.jetstream()
    sub = await js.pull_subscribe("stock.results", durable=None)

    event = anomaly_event_pb2.AnomalyEvent(
        correlation_id=correlation_id,
        ticker=ticker,
        trigger_type="PRICE_CHANGE",
        price_change_pct=-8.0,
        volume_ratio=0.0,
    )
    event.detected_at.GetCurrentTime()
    await js.publish("stock.anomaly", event.SerializeToString())
    print(f"[1/3] published synthetic anomaly correlation_id={correlation_id}")

    found = None
    loop = asyncio.get_event_loop()
    deadline = loop.time() + TIMEOUT_SECONDS
    while loop.time() < deadline:
        try:
            msgs = await sub.fetch(batch=10, timeout=3)
        except Exception:
            continue
        for msg in msgs:
            analysis = ai_analysis_pb2.AiAnalysis()
            analysis.ParseFromString(msg.data)
            await msg.ack()
            if analysis.correlation_id == correlation_id:
                found = analysis
        if found:
            break

    await nc.close()

    if found is None:
        print(f"[FAIL] tidak ada hasil analisis di stock.results dalam {TIMEOUT_SECONDS} detik")
        return 1
    print(f"[2/3] hasil analisis diterima: sentiment={found.sentiment} risk_level={found.risk_level}")

    conn = await asyncpg.connect(DATABASE_URL)
    row = None
    deadline = loop.time() + TIMEOUT_SECONDS
    while loop.time() < deadline:
        row = await conn.fetchrow(
            "SELECT ticker, summary, sentiment, risk_level FROM ai_analyses WHERE correlation_id = $1",
            correlation_id,
        )
        if row:
            break
        await asyncio.sleep(1)
    await conn.close()

    if row is None:
        print("[FAIL] hasil analisis tidak pernah masuk ke tabel ai_analyses")
        return 1
    if row["ticker"] != ticker:
        print(f"[FAIL] ticker salah di Postgres: expected {ticker}, got {row['ticker']}")
        return 1

    print(f"[3/3] terverifikasi di Postgres: {dict(row)}")
    print("INTEGRATION TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

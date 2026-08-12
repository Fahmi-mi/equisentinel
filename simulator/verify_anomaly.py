import asyncio
import nats
from proto_gen import anomaly_event_pb2


def print_event(subject: str, data: bytes) -> None:
    event = anomaly_event_pb2.AnomalyEvent()
    event.ParseFromString(data)
    print(
        f"[{subject}] ticker={event.ticker} trigger={event.trigger_type} "
        f"price_change_pct={event.price_change_pct:.2f} volume_ratio={event.volume_ratio:.2f} "
        f"correlation_id={event.correlation_id}"
    )


async def watch(js, subject: str) -> None:
    sub = await js.subscribe(subject, stream="STOCK_ANOMALY")
    while True:
        msg = await sub.next_msg(timeout=None)
        print_event(msg.subject, msg.data)
        await msg.ack()


async def main() -> None:
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    print("Waiting for anomaly events...")
    await asyncio.gather(
        watch(js, "stock.anomaly"),
        watch(js, "stock.anomaly.critical"),
    )


asyncio.run(main())

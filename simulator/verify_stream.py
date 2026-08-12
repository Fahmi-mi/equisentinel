import asyncio
import nats


async def main() -> None:
    nc = await nats.connect("nats://localhost:4222")
    js = nc.jetstream()

    sub = await js.subscribe("stock.quotes.*", stream="STOCK_QUOTES")
    for _ in range(3):
        msg = await sub.next_msg(timeout=10)
        print(msg.subject, len(msg.data), "bytes")
        await msg.ack()

    await nc.close()


asyncio.run(main())

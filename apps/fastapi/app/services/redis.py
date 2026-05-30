import json
import asyncio
from typing import AsyncIterator, Optional

from redis.asyncio import Redis

redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url("redis://localhost:6379", decode_responses=True)
    return redis_client


async def ensure_consumer_group(stream: str, group: str) -> None:
    r = await get_redis()
    try:
        await r.xgroup_create(stream, group, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise


async def consume_stream(
    stream: str,
    group: str,
    consumer: str,
    batch_size: int = 5,
    block: int = 2000,
) -> AsyncIterator[tuple[str, dict]]:
    r = await get_redis()
    while True:
        try:
            result = await r.xreadgroup(
                group, consumer, {stream: ">"},
                count=batch_size, block=block,
            )
            if not result:
                await asyncio.sleep(0.1)
                continue
            for messages in result.values():
                for msg_id, fields in messages:
                    yield str(msg_id), json.loads(fields["payload"])
        except Exception as e:
            print(f"[redis] consume error: {e}")
            await asyncio.sleep(1)


async def publish_to_stream(stream: str, payload: dict) -> None:
    r = await get_redis()
    await r.xadd(stream, "*", {"payload": json.dumps(payload)})


async def ack_message(stream: str, group: str, msg_id: str) -> None:
    r = await get_redis()
    await r.xack(stream, group, msg_id)

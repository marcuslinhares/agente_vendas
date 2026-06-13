import asyncio
import json
from collections.abc import AsyncIterator

from redis.asyncio import Redis

from app.config import settings

redis_client: Redis | None = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
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
                group,
                consumer,
                {stream: ">"},
                count=batch_size,
                block=block,
            )
            if not result:
                await asyncio.sleep(0.1)
                continue
            for messages in result.values():  # type: ignore[union-attr]
                for msg_id, fields in messages:  # type: ignore[misc]
                    yield str(msg_id), json.loads(fields["payload"])  # type: ignore[index,arg-type,call-overload]
        except Exception as e:
            print(f"[redis] consume error: {e}")
            await asyncio.sleep(1)


async def publish_to_stream(stream: str, payload: dict) -> None:
    r = await get_redis()
    await r.xadd(stream, "*", {"payload": json.dumps(payload)})  # type: ignore[arg-type]


async def ack_message(stream: str, group: str, msg_id: str) -> None:
    r = await get_redis()
    await r.xack(stream, group, msg_id)

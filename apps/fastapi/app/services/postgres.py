from typing import Optional

import asyncpg

from app.config import settings

pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
    return pool


async def get_last_messages(conversation_id: str, limit: int = 10) -> list[dict]:
    p = await get_pool()
    rows = await p.fetch(
        """SELECT role, content, media_url, media_type, created_at
           FROM messages
           WHERE conversation_id = $1
           ORDER BY created_at DESC
           LIMIT $2""",
        conversation_id, limit
    )
    return [dict(r) for r in rows]


async def get_conversation_summary(conversation_id: str) -> Optional[str]:
    p = await get_pool()
    row = await p.fetchrow(
        "SELECT summary FROM conversations WHERE id = $1",
        conversation_id
    )
    return row["summary"] if row else None


async def get_conversation_by_whatsapp(whatsapp_id: str) -> Optional[dict]:
    p = await get_pool()
    row = await p.fetchrow(
        "SELECT id, status, message_count FROM conversations WHERE whatsapp_id = $1",
        whatsapp_id
    )
    return dict(row) if row else None


async def create_conversation(whatsapp_id: str) -> dict:
    p = await get_pool()
    row = await p.fetchrow(
        """INSERT INTO conversations (whatsapp_id)
           VALUES ($1)
           RETURNING id, status, message_count""",
        whatsapp_id
    )
    return dict(row)


async def increment_message_count(conversation_id: str) -> None:
    p = await get_pool()
    await p.execute(
        "UPDATE conversations SET message_count = message_count + 1, updated_at = NOW() WHERE id = $1",
        conversation_id
    )


async def vector_search(
    conversation_id: str,
    embedding: list[float],
    cutoff: str,
    limit: int = 5,
    threshold: float = 0.75,
) -> list[dict]:
    p = await get_pool()
    rows = await p.fetch(
        """SELECT content, media_url, media_type,
                   1 - (embedding <=> $1::vector) AS score
           FROM message_embeddings
           WHERE conversation_id = $2 AND created_at < $3::timestamptz
             AND 1 - (embedding <=> $1::vector) > $4
           ORDER BY score DESC
           LIMIT $5""",
        embedding, conversation_id, cutoff, threshold, limit
    )
    return [dict(r) for r in rows]

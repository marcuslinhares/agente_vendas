"""Semantic cache for LLM responses using Redis + embeddings."""

import hashlib
from typing import Optional


async def _get_redis():
    from app.services.redis import get_redis

    return await get_redis()


def _simple_hash(text: str) -> str:
    """Fast hash for exact-match cache lookup."""
    return hashlib.md5(text.encode()).hexdigest()


async def get_cached_response(user_message: str) -> Optional[str]:
    """
    Check semantic cache for a similar question.
    Returns cached response if found, None otherwise.
    """
    if not user_message:
        return None

    r = await _get_redis()

    # 1. Try exact-match cache first (fast)
    exact_key = f"cache:exact:{_simple_hash(user_message)}"
    exact = await r.get(exact_key)
    if exact:
        return exact

    # 2. Try semantic cache via sorted set (needs embedding)
    # For now, only exact-match is implemented
    # Semantic matching via embedding will be added in future

    return None


async def set_cached_response(
    user_message: str, response: str, ttl: int = 3600
) -> None:
    """Cache a response for future similar questions."""
    if not user_message or not response:
        return

    r = await _get_redis()

    # Exact-match cache
    exact_key = f"cache:exact:{_simple_hash(user_message)}"
    await r.setex(exact_key, ttl, response)

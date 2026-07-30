"""Per-user fixed-window rate limiting backed by Redis."""
import time

import redis.asyncio as redis
from fastapi import HTTPException, status

from app.config import settings

_redis: redis.Redis | None = None


def _client() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _limit_for_plan(plan: str) -> int:
    return settings.rate_limit_pro if plan == "pro" else settings.rate_limit_free


async def enforce_rate_limit(user) -> None:
    """Allow `limit` requests per rolling 60s window per user. Raises 429 if exceeded."""
    limit = _limit_for_plan(user.plan)
    window = int(time.time() // 60)
    key = f"rl:{user.id}:{window}"

    client = _client()
    current = await client.incr(key)
    if current == 1:
        await client.expire(key, 60)
    if current > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({limit}/min for '{user.plan}' plan).",
        )

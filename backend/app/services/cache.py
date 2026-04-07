"""
Redis caching for LLM triage responses.
Cache key: SHA-256 hash of the transcript (normalised).
TTL: 5 minutes (300 seconds).
"""
import hashlib
import json
import redis.asyncio as aioredis
from app.config import settings
from app.models.schemas import TriageResult

TTL_SECONDS = 300
_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _cache_key(transcript: str) -> str:
    normalised = transcript.lower().strip()
    digest = hashlib.sha256(normalised.encode()).hexdigest()
    return f"shield:triage:{digest}"


async def get_cached(transcript: str) -> TriageResult | None:
    """Return cached TriageResult for transcript, or None if not cached."""
    try:
        r = get_redis()
        raw = await r.get(_cache_key(transcript))
        if raw:
            return TriageResult(**json.loads(raw))
    except Exception as e:
        print(f"[Cache] Redis GET error: {e}")
    return None


async def set_cached(transcript: str, result: TriageResult) -> None:
    """Cache a TriageResult for 5 minutes."""
    try:
        r = get_redis()
        await r.setex(_cache_key(transcript), TTL_SECONDS, result.model_dump_json())
    except Exception as e:
        print(f"[Cache] Redis SET error: {e}")

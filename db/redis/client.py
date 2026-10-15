"""
Redis 客户端与公共能力：
- 会话/状态缓存（TTL 自动过期）
- 滑动窗口限流
- 摄入任务队列（List 结构）
- 高频 query 检索结果缓存
"""
from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as aioredis

from core.config import settings
from core.logging import get_logger

logger = get_logger("db.redis")

_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _pool


async def close_redis() -> None:
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ---------------- 限流（滑动窗口） ----------------
async def is_allowed(ident: str, qps: int | None = None) -> bool:
    """基于 Redis 滑动窗口的限流，返回是否放行。"""
    qps = qps or settings.RATE_LIMIT_QPS
    r = await get_redis()
    key = f"ratelimit:{ident}"
    now = await r.time()
    now_ms = now[0] * 1000 + now[1] // 1000
    async with r.pipeline() as pipe:
        pipe.zremrangebyscore(key, 0, now_ms - 1000)
        pipe.zadd(key, {str(now_ms): now_ms})
        pipe.expire(key, 2)
        pipe.zcard(key)
        _, _, _, count = await pipe.execute()
    return int(count) <= qps


# ---------------- 通用缓存 ----------------
async def cache_get(key: str) -> Optional[dict]:
    r = await get_redis()
    raw = await r.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: dict, ttl: int = 600) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)


def query_cache_key(kb_id: str, query: str, top_k: int) -> str:
    import hashlib

    h = hashlib.md5(f"{kb_id}:{query}:{top_k}".encode()).hexdigest()
    return f"qcache:{h}"


# ---------------- 任务队列 ----------------
async def enqueue(task: dict) -> None:
    r = await get_redis()
    await r.rpush(settings.INGEST_QUEUE, json.dumps(task, ensure_ascii=False))


async def dequeue(timeout: int = 5) -> Optional[dict]:
    r = await get_redis()
    raw = await r.blpop(settings.INGEST_QUEUE, timeout=timeout)
    if not raw:
        return None
    return json.loads(raw[1])


async def publish_progress(task_id: str, payload: dict) -> None:
    """通过 Redis 发布任务进度，前端可订阅 channel 获取异步摄入状态。"""
    r = await get_redis()
    await r.publish(f"ingest:progress:{task_id}", json.dumps(payload, ensure_ascii=False))

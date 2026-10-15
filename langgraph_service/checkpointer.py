"""
Redis Checkpointer（分布式 Agent 状态持久化）
- 多实例部署时共享会话状态，支持断点恢复（对应文章避坑清单第 1 条）
- Redis 不可用时降级为内存 Checkpointer，保证本地可跑
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver

from core.config import settings
from core.logging import get_logger

logger = get_logger("lg.checkpointer")

_checkpointer = None


async def get_checkpointer():
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer
    try:
        from langgraph.checkpoint.redis.aio import RedisSaver

        saver = RedisSaver.from_conn_string(settings.REDIS_URL)
        await saver.setup()
        _checkpointer = saver
        logger.info("using Redis checkpointer")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"redis checkpointer unavailable, fallback MemorySaver: {e}")
        _checkpointer = MemorySaver()
    return _checkpointer

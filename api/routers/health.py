"""健康检查路由：探测各依赖组件可用性"""
from __future__ import annotations

from fastapi import APIRouter

from core.logging import get_logger
from db.redis.client import get_redis

logger = get_logger("api.health")
router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    status: dict = {"api": "ok"}

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        status["redis"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["redis"] = f"error: {e}"

    # MySQL
    try:
        from db.mysql.session import engine

        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        status["mysql"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["mysql"] = f"error: {e}"

    # Elasticsearch
    try:
        from db.es.client import get_es

        es = await get_es()
        await es.info()
        status["elasticsearch"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["elasticsearch"] = f"error: {e}"

    # Milvus
    try:
        from db.milvus.client import _ensure_collection

        _ensure_collection()
        status["milvus"] = "ok"
    except Exception as e:  # noqa: BLE001
        status["milvus"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, "components": status}

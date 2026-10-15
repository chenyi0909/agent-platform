"""限流中间件：基于 Redis 滑动窗口，按用户维度限制 QPS"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from api.middlewares.auth import get_user_id
from db.redis.client import is_allowed


async def rate_limit(user_id: int = Depends(get_user_id), request: Request | None = None) -> None:
    ident = f"u:{user_id}"
    if not await is_allowed(ident):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, please retry later")

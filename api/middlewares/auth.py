"""鉴权中间件：基于 api_key 的用户解析（Bearer Token）"""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException

from db.mysql.models import User
from db.mysql.session import AsyncSessionLocal
from db.redis.client import get_redis
from sqlalchemy import select


async def get_user_id(authorization: str = Header(None)) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    key = authorization.split(" ", 1)[1].strip()

    r = await get_redis()
    cached = await r.get(f"user:{key}")
    if cached:
        return int(cached)

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.api_key == key))
        ).scalar_one_or_none()
        if user is None or user.status != 1:
            raise HTTPException(status_code=401, detail="Invalid or disabled API key")
        await r.set(f"user:{key}", user.id, ex=300)
        return user.id

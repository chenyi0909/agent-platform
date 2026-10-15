"""
FastAPI 应用装配
- 生命周期：日志初始化 -> 建表 -> 默认用户 -> 就绪
- 中间件：trace_id 透传
- 路由：chat / knowledge / agent / health
"""
from __future__ import annotations

import contextlib

from fastapi import FastAPI
from sqlalchemy import select

from api.middlewares.tracing import TracingMiddleware
from api.routers import agent, chat, health, knowledge
from core.config import settings
from core.logging import configure_logging, get_logger
from db.mysql.models import User
from db.mysql.session import AsyncSessionLocal, close_redis, init_db
from db.redis.client import close_redis as close_redis_conn

logger = get_logger("api")


async def _ensure_default_user() -> None:
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.api_key == settings.API_KEY_DEFAULT))
        ).scalar_one_or_none()
        if existing is None:
            session.add(User(name="default", api_key=settings.API_KEY_DEFAULT, status=1))
            await session.commit()
            logger.info("default user created")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    await _ensure_default_user()
    logger.info(f"{settings.APP_NAME} started")
    try:
        yield
    finally:
        await close_redis_conn()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(TracingMiddleware)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(agent.router)
app.include_router(health.router)

"""
MySQL 异步会话管理（SQLAlchemy 2.0 + aiomysql）
仅存储业务元数据：用户、知识库、文档、会话、消息（不含大文本/向量）。
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from core.logging import get_logger

logger = get_logger("db.mysql")

engine = create_async_engine(settings.MYSQL_ASYNC_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """建表（首次启动）。生产环境建议改用 Alembic 迁移。"""
    from db.mysql import models  # noqa: F401 确保模型注册

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    logger.info("mysql tables initialized")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

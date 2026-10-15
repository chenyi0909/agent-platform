"""
统一配置中心（pydantic-settings）
所有模块统一从此处读取配置，避免散落环境变量。
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # 基础
    ENV: str = "production"
    APP_NAME: str = "agent-platform"
    LOG_LEVEL: str = "INFO"

    # LLM（OpenAI 兼容）
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 1024
    LLM_SKIP_AUTH: bool = False

    # Embedding（OpenAI 兼容）
    EMBED_BASE_URL: str = "https://api.openai.com/v1"
    EMBED_API_KEY: str = ""
    EMBED_MODEL: str = "text-embedding-3-small"
    EMBED_DIM: int = 1536
    EMBED_SKIP_AUTH: bool = False

    # Rerank
    RERANK_ENDPOINT: str = ""
    RERANK_MODEL: str = ""

    # MySQL
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "agent"
    MYSQL_PASSWORD: str = "agent123"
    MYSQL_DATABASE: str = "agent_platform"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Milvus
    MILVUS_HOST: str = "milvus"
    MILVUS_PORT: int = 19530

    # Elasticsearch
    ES_HOST: str = "http://elasticsearch:9200"
    ES_USER: str = "elastic"
    ES_PASSWORD: str = ""

    # 鉴权
    AUTH_SECRET: str = "change-me-in-prod"
    API_KEY_DEFAULT: str = "dev-key-123456"

    # 限流
    RATE_LIMIT_QPS: int = 5

    # 摄入
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 80
    INGEST_QUEUE: str = "ingest_queue"

    # 派生：异步 MySQL URL（aiomysql）
    @property
    def MYSQL_ASYNC_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"
        )

    @property
    def MILVUS_COLLECTION(self) -> str:
        return "rag_chunks"

    @property
    def ES_INDEX(self) -> str:
        return "rag_chunks"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

"""
LLM / Embedding 客户端（OpenAI 兼容）
可指向云端或本地部署大模型（如 One API、vLLM、Ollama 等 OpenAI 兼容网关）。
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from core.config import settings


def _llm_key() -> str:
    return "" if settings.LLM_SKIP_AUTH else (settings.LLM_API_KEY or "sk-noauth")


def _embed_key() -> str:
    return "" if settings.EMBED_SKIP_AUTH else (settings.EMBED_API_KEY or "sk-noauth")


@lru_cache
def get_llm() -> BaseChatModel:
    """返回非流式 Chat 模型（生成节点使用）。"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=_llm_key(),
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        streaming=False,
        disable_streaming=True,
    )


@lru_cache
def get_llm_stream() -> BaseChatModel:
    """返回流式 Chat 模型（SSE 输出使用）。"""
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=_llm_key(),
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        streaming=True,
    )


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.EMBED_BASE_URL,
        api_key=_embed_key(),
        check_embedded_within_list=False,
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量向量化，返回定长向量列表。"""
    return get_embeddings().embed_documents(texts)

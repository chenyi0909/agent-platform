"""
Elasticsearch 客户端（全文检索 / 原文存储）
设计要点：
- 存储文档切片原文（Milvus 只存向量，通过 doc_id 关联）
- 关键词检索 + 按 kb_id 过滤，返回原文用于生成与高亮
"""
from __future__ import annotations

from typing import Optional

from elasticsearch import AsyncElasticsearch

from core.config import settings
from core.logging import get_logger

logger = get_logger("db.es")

_client: Optional[AsyncElasticsearch] = None


def _build() -> AsyncElasticsearch:
    if settings.ES_PASSWORD:
        return AsyncElasticsearch(
            settings.ES_HOST,
            basic_auth=(settings.ES_USER, settings.ES_PASSWORD),
        )
    return AsyncElasticsearch(settings.ES_HOST)


async def get_es() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = _build()
        if not await _client.indices.exists(index=settings.ES_INDEX):
            await _client.indices.create(
                index=settings.ES_INDEX,
                mappings={
                    "properties": {
                        "doc_id": {"type": "keyword"},
                        "kb_id": {"type": "keyword"},
                        "text": {"type": "text", "analyzer": "standard"},
                        "source": {"type": "keyword"},
                    }
                },
            )
        logger.info(f"es index '{settings.ES_INDEX}' ready")
    return _client


async def index_chunk(doc_id: str, kb_id: str, text: str, source: str = "upload") -> None:
    es = await get_es()
    await es.index(
        index=settings.ES_INDEX,
        id=doc_id,
        document={"doc_id": doc_id, "kb_id": kb_id, "text": text, "source": source},
    )


async def search(query: str, kb_id: str, top_k: int = 5) -> list[dict]:
    es = await get_es()
    body = {
        "query": {
            "bool": {
                "must": [{"match": {"text": query}}],
                "filter": [{"term": {"kb_id": kb_id}}],
            }
        },
        "size": top_k,
        "_source": ["doc_id", "text", "source"],
    }
    resp = await es.search(index=settings.ES_INDEX, body=body)
    return [
        {
            "doc_id": h["_source"]["doc_id"],
            "text": h["_source"]["text"],
            "source": h["_source"]["source"],
            "score": float(h["_score"] or 0.0),
        }
        for h in resp["hits"]["hits"]
    ]


async def mget_texts(doc_ids: list[str]) -> dict[str, str]:
    """批量取回原文，返回 {doc_id: text}。"""
    es = await get_es()
    if not doc_ids:
        return {}
    resp = await es.mget(index=settings.ES_INDEX, ids=doc_ids)
    out = {}
    for doc in resp["docs"]:
        if doc.get("found"):
            out[doc["_id"]] = doc["_source"]["text"]
    return out

"""
检索节点：并行召回 + 融合重排
- Milvus 向量召回（语义相似）
- ES 全文召回（关键词/过滤）
- Redis 缓存高频 query 的 topK 结果
- 融合（RRF / 远程 Rerank）后组装 context
"""
from __future__ import annotations

import time

from core.llm import embed_texts
from core.logging import get_logger
from core.rerank import Hit, remote_rerank
from db.es.client import mget_texts, search as es_search
from db.milvus.client import search as milvus_search
from db.redis.client import cache_get, cache_set, query_cache_key
from langgraph_service.graph.states import AgentState

logger = get_logger("lg.retriever")


async def _cached_or_search(kb_id: int, query: str, top_k: int) -> list[Hit] | None:
    key = query_cache_key(str(kb_id), query, top_k)
    cached = await cache_get(key)
    if cached:
        return [Hit(**h) for h in cached]
    return None


async def retriever_node(state: AgentState) -> dict:
    kb_id = state["kb_id"]
    query = state["query"]
    top_k = 5

    cached = await _cached_or_search(kb_id, query, top_k)
    if cached:
        fused = cached
    else:
        vec = embed_texts([query])[0]
        mv = milvus_search(str(kb_id), vec, top_k)
        es = await es_search(query, str(kb_id), top_k)

        hits: list[Hit] = []
        for h in mv:
            hits.append(Hit(doc_id=h["doc_id"], text=h["text"], source="milvus", score=h["score"]))
        for h in es:
            hits.append(Hit(doc_id=h["doc_id"], text=h["text"], source="es", score=h["score"]))

        fused = await remote_rerank(query, hits, top_k)
        # 缓存（命中可降低 Milvus/ES 压力）
        await cache_set(query_cache_key(str(kb_id), query, top_k), [h.__dict__ for h in fused], ttl=600)

    context_docs = [h.text for h in fused if h.text]
    if not context_docs:
        # 兜底：从 ES 取回原文（防向量/全文均空）
        ids = [h.doc_id for h in fused]
        texts = await mget_texts(ids)
        context_docs = [texts[i] for i in ids if i in texts]

    context = "\n\n".join(f"[{i+1}] {t}" for i, t in enumerate(context_docs))
    return {
        "milvus_hits": [h.__dict__ for h in fused if h.source == "milvus"],
        "es_hits": [h.__dict__ for h in fused if h.source == "es"],
        "fused_hits": [h.__dict__ for h in fused],
        "context": context,
    }

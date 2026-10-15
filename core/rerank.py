"""
检索结果重排
策略：
1. 若配置了 RERANK_ENDPOINT（如 BGE-Reranker 的 OpenAI 兼容重排接口），
   则调用远程重排服务得到精排分数；
2. 否则使用 RRF（Reciprocal Rank Fusion）对多路召回做融合重排，
   无需额外模型即可获得稳定的混合排序。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import httpx

from core.config import settings
from core.logging import get_logger

logger = get_logger("core.rerank")


@dataclass
class Hit:
    doc_id: str
    text: str
    source: str          # milvus / es
    score: float = 0.0    # 归一化后的单路分数
    rank: int = 0         # 融合后的全局排名（用于去重）


def _rrf(ranks: list[int], k: int = 60) -> float:
    return sum(1.0 / (k + r) for r in ranks if r > 0)


def fuse(hits: list[Hit], top_n: int = 8) -> list[Hit]:
    """多路召回融合重排（RRF），按融合分数降序返回前 top_n。"""
    seen: dict[str, list[int]] = {}
    for idx, h in enumerate(hits):
        seen.setdefault(h.doc_id, []).append(idx + 1)

    fused: list[Hit] = []
    for doc_id, ranks in seen.items():
        rep = next(h for h in hits if h.doc_id == doc_id)
        rep.score = _rrf(ranks)
        fused.append(rep)

    fused.sort(key=lambda x: x.score, reverse=True)
    for i, h in enumerate(fused):
        h.rank = i + 1
    return fused[:top_n]


async def remote_rerank(query: str, hits: list[Hit], top_n: int = 8) -> list[Hit]:
    """调用远程重排端点（兼容 Cohere/Jina 风格 rerank 接口）。"""
    if not settings.RERANK_ENDPOINT:
        return fuse(hits, top_n)

    payload = {
        "model": settings.RERANK_MODEL or "bge-reranker",
        "query": query,
        "documents": [h.text for h in hits],
        "top_n": min(top_n, len(hits)),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.RERANK_ENDPOINT, json=payload)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results", [])
        order = sorted(results, key=lambda r: r.get("relevance_score", 0), reverse=True)
        out: list[Hit] = []
        for i, r in enumerate(order):
            idx = r.get("index", i)
            h = hits[idx]
            h.score = float(r.get("relevance_score", 0.0))
            h.rank = i + 1
            out.append(h)
        return out[:top_n]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"remote rerank failed, fallback to RRF: {e}")
        return fuse(hits, top_n)


# 同步包装（供非 async 节点使用）
def fuse_sync(hits: list[Hit], top_n: int = 8) -> list[Hit]:
    return fuse(hits, top_n)


def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)

"""
Rerank 节点（可选，独立封装供 graph 复用）
实际融合逻辑在 core.rerank，这里提供可被 graph 直连的节点，
便于后续替换为独立的重排服务或 BGE-Reranker 模型。
"""
from __future__ import annotations

from core.rerank import Hit, remote_rerank
from langgraph_service.graph.states import AgentState


async def rerank_node(state: AgentState) -> dict:
    query = state["query"]
    hits: list[Hit] = []
    for h in state.get("milvus_hits", []) + state.get("es_hits", []):
        hits.append(Hit(doc_id=h["doc_id"], text=h["text"], source=h.get("source", "unknown")))
    fused = await remote_rerank(query, hits, top_k=5)
    return {"fused_hits": [h.__dict__ for h in fused]}

"""Agent 编排信息路由（展示当前 graph 的节点与链路）"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/graph")
async def graph_info():
    return {
        "name": "rag-graph",
        "entry": "router",
        "nodes": ["router", "retriever", "generator"],
        "edges": {
            "router": ["retrieve->retriever", "generate->generator"],
            "retriever": ["generator"],
            "generator": ["END"],
        },
        "retrieval": ["milvus(vector)", "elasticsearch(fulltext)", "rerank(RRF/remote)"],
        "checkpointer": "redis",
    }

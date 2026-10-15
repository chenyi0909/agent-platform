"""
LangGraph 客户端：对外提供同步问答与流式问答两种入口
- run()：一次性返回最终答案
- stream_tokens()：异步生成器，逐 token 产出（供 SSE 使用）
"""
from __future__ import annotations

from typing import AsyncGenerator

from langgraph_service.graph.rag_graph import build_graph
from langgraph_service.graph.states import AgentState


async def run(query: str, user_id: int, kb_id: int, thread_id: str) -> dict:
    graph = await build_graph()
    state: AgentState = {
        "query": query,
        "user_id": user_id,
        "kb_id": kb_id,
        "messages": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(state, config)
    return {
        "answer": result.get("answer", ""),
        "context": result.get("context", ""),
        "fused_hits": result.get("fused_hits", []),
        "error": result.get("error", ""),
    }


async def stream_tokens(query: str, user_id: int, kb_id: int, thread_id: str) -> AsyncGenerator[str, None]:
    """逐个 token 产出；最后从 checkpoint 取回完整答案。"""
    graph = await build_graph()
    state: AgentState = {
        "query": query,
        "user_id": user_id,
        "kb_id": kb_id,
        "messages": [],
    }
    config = {"configurable": {"thread_id": thread_id}}
    async for chunk, _meta in graph.astream(state, config, stream_mode="messages"):
        content = getattr(chunk, "content", None)
        if content:
            yield content

    # 取最终答案（含上下文与引用）
    snap = await graph.aget_state(config)
    final = snap.values or {}
    yield "\n__META__" + _meta_payload(final)


def _meta_payload(final: dict) -> str:
    import json

    return json.dumps(
        {
            "context": final.get("context", ""),
            "fused_hits": final.get("fused_hits", []),
            "error": final.get("error", ""),
        },
        ensure_ascii=False,
    )

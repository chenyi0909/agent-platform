"""
路由节点：判断用户问题是否需要检索知识库
- 走 LLM 分类（更准），失败则默认检索，保证可用性
"""
from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from core.llm import get_llm
from core.logging import get_logger
from langgraph_service.graph.states import AgentState

logger = get_logger("lg.router")

ROUTE_PROMPT = (
    "你是智能体中台的路由决策器。判断用户问题是否需要检索知识库来回答。\n"
    "需要检索的情况：询问事实、文档内容、特定资料、带知识库上下文的问题。\n"
    "无需检索的情况：纯闲聊、问候、或可用通用知识直接回答的简单问题。\n"
    "只回复一个词：retrieve 或 generate。"
)


async def router_node(state: AgentState) -> dict:
    query = state.get("query", "")
    try:
        llm = get_llm()
        resp = await llm.ainvoke(
            [SystemMessage(content=ROUTE_PROMPT), HumanMessage(content=query)]
        )
        decision = "generate" if "generate" in resp.content.lower() else "retrieve"
    except Exception as e:  # noqa: BLE001
        logger.warning(f"router llm failed, default retrieve: {e}")
        decision = "retrieve"
    return {"route_decision": decision}

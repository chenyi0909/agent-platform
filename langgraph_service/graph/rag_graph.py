"""
RAG 工作流图定义
流程：router -(retrieve)-> retriever -> generator -> END
                  -(generate)-> generator -> END
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from core.logging import get_logger
from langgraph_service.checkpointer import get_checkpointer
from langgraph_service.graph.states import AgentState
from langgraph_service.nodes.generator import generator_node
from langgraph_service.nodes.retriever import retriever_node
from langgraph_service.nodes.router import router_node

logger = get_logger("lg.graph")

_graph = None


def _route(state: AgentState) -> str:
    return state.get("route_decision", "retrieve")


async def build_graph():
    global _graph
    if _graph is not None:
        return _graph

    builder = StateGraph(AgentState)
    builder.add_node("router", router_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("generator", generator_node)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", _route, path_map={"retrieve": "retriever", "generate": "generator"}
    )
    builder.add_edge("retriever", "generator")
    builder.add_edge("generator", END)

    checkpointer = await get_checkpointer()
    _graph = builder.compile(checkpointer=checkpointer)
    logger.info("rag graph compiled")
    return _graph

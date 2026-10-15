"""
Agent 状态定义（LangGraph StateGraph 共享状态）
仅保存轻量字段；大上下文/长对话通过 Redis Checkpoint 持久化。
"""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langgraph.graph import MessagesState  # 提供 messages 累加通道
from langchain_core.messages import BaseMessage


class AgentState(MessagesState):
    query: str
    user_id: int
    kb_id: int
    route_decision: str = "retrieve"      # retrieve | generate
    milvus_hits: list[dict] = []
    es_hits: list[dict] = []
    fused_hits: list[dict] = []
    context: str = ""
    answer: str = ""
    error: str = ""

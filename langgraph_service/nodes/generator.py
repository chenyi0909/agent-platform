"""
生成节点：基于召回上下文调用 LLM 产出答案
- 使用流式 LLM，token 可被 graph.astream(stream_mode="messages") 捕获
- 将答案写入 state.answer，并追加到 messages 通道
"""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.llm import get_llm_stream
from core.logging import get_logger
from langgraph_service.graph.states import AgentState

logger = get_logger("lg.generator")

SYSTEM_PROMPT = (
    "你是企业智能助理，严格基于下方【参考材料】回答用户问题。\n"
    "要求：1) 仅使用参考材料中的信息；2) 材料不足时明确说明无法回答；"
    "3) 引用材料编号；4) 语言简洁准确。"
)


async def generator_node(state: AgentState) -> dict:
    query = state["query"]
    context = state.get("context", "")

    if context:
        user_content = f"【参考材料】\n{context}\n\n【问题】{query}"
    else:
        user_content = query

    llm = get_llm_stream()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    answer = ""
    try:
        async for chunk in llm.astream(messages):
            answer += chunk.content or ""
    except Exception as e:  # noqa: BLE001
        logger.error(f"generator llm failed: {e}")
        return {"answer": "", "error": str(e)}

    return {"answer": answer, "messages": [AIMessage(content=answer)]}

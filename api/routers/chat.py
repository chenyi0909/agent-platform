"""
对话路由：提供流式(SSE)与非流式两种问答接口
- POST /api/chat/stream ：SSE 逐 token 返回，降低首字延迟
- POST /api/chat        ：一次性返回（便于测试）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.middlewares.auth import get_user_id
from api.middlewares.ratelimit import rate_limit
from api.schemas.chat import ChatRequest, ChatResponse
from core.logging import get_logger
from langgraph_service.client import run, stream_tokens

logger = get_logger("api.chat")
router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream", dependencies=[Depends(rate_limit)])
async def chat_stream(req: ChatRequest, user_id: int = Depends(get_user_id)):
    from sse_starlette.sse import EventSourceResponse

    thread_id = req.thread_id or f"{user_id}-{req.kb_id}"

    async def gen():
        try:
            async for token in stream_tokens(req.query, user_id, req.kb_id, thread_id):
                if token.startswith("\n__META__"):
                    yield {"event": "meta", "data": token[len("\n__META__"):]}
                else:
                    yield {"event": "token", "data": token}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as e:  # noqa: BLE001
            logger.error(f"chat stream error: {e}")
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(gen())


@router.post("/", response_model=ChatResponse, dependencies=[Depends(rate_limit)])
async def chat(req: ChatRequest, user_id: int = Depends(get_user_id)):
    thread_id = req.thread_id or f"{user_id}-{req.kb_id}"
    result = await run(req.query, user_id, req.kb_id, thread_id)
    return ChatResponse(
        answer=result["answer"],
        context=result["context"],
        references=result["fused_hits"],
        error=result["error"],
    )

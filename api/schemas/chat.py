"""请求/响应模型（Pydantic v2）"""
from __future__ import annotations

from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    kb_id: int
    thread_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    context: str = ""
    references: list[dict] = []
    error: str = ""


class KBCreate(BaseModel):
    name: str


class KBResponse(BaseModel):
    id: int
    name: str
    status: int = 1


class UploadResponse(BaseModel):
    task_id: str
    doc_id: int
    status: str = "queued"

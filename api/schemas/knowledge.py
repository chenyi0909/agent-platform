"""知识库相关请求/响应模型（Pydantic v2）"""
from __future__ import annotations

from pydantic import BaseModel


class KBCreate(BaseModel):
    name: str


class KBResponse(BaseModel):
    id: int
    name: str
    status: int = 1


class DocResponse(BaseModel):
    id: int
    kb_id: int
    file_name: str
    status: int
    chunk_count: int = 0

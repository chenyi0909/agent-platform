"""
知识库与文档摄入路由
- 创建知识库
- 上传文档（异步：API 仅解析入队，worker 后台切分/向量化/入库）
- 查询知识库与文档状态
"""
from __future__ import annotations

import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.middlewares.auth import get_user_id
from api.middlewares.ratelimit import rate_limit
from api.schemas.knowledge import DocResponse, KBResponse, KBCreate, UploadResponse
from core.logging import get_logger
from db.milvus.client import _ensure_collection  # noqa: F401 触发 Milvus 就绪
from db.mysql.models import Document, KnowledgeBase
from db.mysql.session import AsyncSessionLocal
from db.redis.client import enqueue
from ingest.parser import parse_upload
from sqlalchemy import select

logger = get_logger("api.knowledge")
router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("", response_model=KBResponse, dependencies=[Depends(rate_limit)])
async def create_kb(body: KBCreate, user_id: int = Depends(get_user_id)):
    async with AsyncSessionLocal() as session:
        kb = KnowledgeBase(name=body.name, owner_id=user_id, status=1)
        session.add(kb)
        await session.flush()
        await session.refresh(kb)
        await session.commit()
        return KBResponse(id=kb.id, name=kb.name)


@router.get("", response_model=list[KBResponse])
async def list_kb(user_id: int = Depends(get_user_id)):
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(KnowledgeBase).where(KnowledgeBase.owner_id == user_id))).scalars().all()
        return [KBResponse(id=r.id, name=r.name, status=r.status) for r in rows]


@router.post("/{kb_id}/documents", response_model=UploadResponse, dependencies=[Depends(rate_limit)])
async def upload_doc(kb_id: int, file: UploadFile = File(...), user_id: int = Depends(get_user_id)):
    data = await file.read()
    try:
        text = parse_upload(file.filename or "file.txt", data)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"parse failed: {e}")

    file_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
    async with AsyncSessionLocal() as session:
        doc = Document(kb_id=kb_id, file_name=file.filename or "file", file_hash=file_hash, status=0)
        session.add(doc)
        await session.flush()
        await session.refresh(doc)
        doc_id = doc.id
        await session.commit()

    task_id = uuid.uuid4().hex
    await enqueue(
        {
            "task_id": task_id,
            "kb_id": kb_id,
            "doc_id": doc_id,
            "file_name": file.filename,
            "text": text,
        }
    )
    logger.info(f"enqueued ingest task {task_id} doc {doc_id} kb {kb_id}")
    return UploadResponse(task_id=task_id, doc_id=doc_id)


@router.get("/{kb_id}/documents", response_model=list[DocResponse])
async def list_docs(kb_id: int, user_id: int = Depends(get_user_id)):
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Document).where(Document.kb_id == kb_id))).scalars().all()
        return [
            DocResponse(id=r.id, kb_id=r.kb_id, file_name=r.file_name, status=r.status, chunk_count=r.chunk_count)
            for r in rows
        ]

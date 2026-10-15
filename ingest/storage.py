"""
存储写入：Milvus（向量）+ ES（原文）+ MySQL（文档状态）
分层写入，避免大文本进 MySQL、长文本进 Milvus。
"""
from __future__ import annotations

from core.llm import embed_texts
from core.logging import get_logger
from db.es.client import index_chunk as es_index_chunk
from db.milvus.client import insert_chunks as milvus_insert
from db.mysql.models import Document
from db.mysql.session import AsyncSessionLocal

logger = get_logger("ingest.storage")


async def _update_doc(doc_id: int, status: int, chunk_count: int = 0) -> None:
    async with AsyncSessionLocal() as session:
        doc = await session.get(Document, doc_id)
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            await session.commit()


async def store(kb_id: int, doc_id: int, file_name: str, chunks: list[str]) -> int:
    """将切片向量化并写入 Milvus + ES，更新 MySQL 文档状态。返回切片数。"""
    await _update_doc(doc_id, 1)  # 处理中
    try:
        if not chunks:
            await _update_doc(doc_id, 2, 0)
            return 0

        vectors = embed_texts(chunks)
        records = []
        for i, (text, vec) in enumerate(zip(chunks, vectors)):
            cid = f"{doc_id}:{i}"
            records.append(
                {"doc_id": cid, "text": text, "source": "upload", "embedding": vec}
            )
            await es_index_chunk(cid, str(kb_id), text, "upload")

        milvus_insert(str(kb_id), records)
        await _update_doc(doc_id, 2, len(chunks))  # 完成
        logger.info(f"stored doc {doc_id} kb {kb_id} chunks={len(chunks)}")
        return len(chunks)
    except Exception as e:  # noqa: BLE001
        logger.error(f"store failed doc {doc_id}: {e}")
        await _update_doc(doc_id, 3)
        raise

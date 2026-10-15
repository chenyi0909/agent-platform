"""
Milvus 客户端（向量检索）
设计要点（对应文章避坑清单）：
- 只存 向量 + 主键 + 元字段(doc_id/kb_id/text/source)，原始长文本交给 ES
- 按知识库 ID 建 partition，检索时仅指定分区，减少资源占用
"""
from __future__ import annotations

from typing import Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from core.config import settings
from core.logging import get_logger

logger = get_logger("db.milvus")

_connected = False


def _connect() -> None:
    global _connected
    if not _connected:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        _connected = True


def _ensure_collection() -> Collection:
    _connect()
    name = settings.MILVUS_COLLECTION
    if utility.has_collection(name):
        return Collection(name)

    fields = [
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema(name="kb_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=32),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBED_DIM),
    ]
    schema = CollectionSchema(fields, description="rag chunk vectors")
    col = Collection(name, schema)
    col.create_index(
        field_name="embedding",
        index_params={"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 8, "efConstruction": 200}},
    )
    col.load()
    logger.info(f"milvus collection '{name}' created & loaded")
    return col


def _ensure_partition(col: Collection, kb_id: str) -> None:
    if not col.has_partition(kb_id):
        col.create_partition(kb_id)


def insert_chunks(kb_id: str, chunks: list[dict]) -> None:
    """chunks: [{"doc_id","text","source","embedding"}]"""
    col = _ensure_collection()
    _ensure_partition(col, kb_id)
    if not chunks:
        return
    data = [
        [c["doc_id"] for c in chunks],
        [kb_id] * len(chunks),
        [c["text"][:4096] for c in chunks],
        [c.get("source", "upload") for c in chunks],
        [c["embedding"] for c in chunks],
    ]
    col.insert(data, partition_name=kb_id)
    col.flush()


def search(kb_id: str, vector: list[float], top_k: int = 5) -> list[dict]:
    col = _ensure_collection()
    _ensure_partition(col, kb_id)
    if not col.has_partition(kb_id):
        return []
    col.load(partition_names=[kb_id])
    res = col.search(
        data=[vector],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": 64}},
        limit=top_k,
        partition_names=[kb_id],
        output_fields=["doc_id", "text", "source"],
    )
    hits = []
    for hit in res[0]:
        hits.append(
            {
                "doc_id": hit.entity.get("doc_id"),
                "text": hit.entity.get("text"),
                "source": hit.entity.get("source"),
                "score": float(hit.score),
            }
        )
    return hits

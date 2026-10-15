"""
摄入 Worker：消费 Redis 任务队列
链路：解析(已在 API 完成) -> 切分 -> 向量化 -> 写入 Milvus+ES+MySQL
全程异步，不阻塞 API 请求（对应文章避坑清单第 3 条）。
"""
from __future__ import annotations

import asyncio
import hashlib

from core.config import settings
from core.logging import get_logger
from db.redis.client import close_redis, dequeue, publish_progress
from ingest.chunker import split_text
from ingest.storage import store

logger = get_logger("ingest.worker")


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


async def process(task: dict) -> None:
    task_id = task.get("task_id", "unknown")
    kb_id = int(task["kb_id"])
    doc_id = int(task["doc_id"])
    text = task.get("text", "")

    await publish_progress(task_id, {"status": "chunking"})
    chunks = split_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    logger.info(f"task {task_id} chunked={len(chunks)}")

    await publish_progress(task_id, {"status": "embedding"})
    n = await store(kb_id, doc_id, task.get("file_name", ""), chunks)
    await publish_progress(task_id, {"status": "done", "chunks": n})


async def main_loop() -> None:
    logger.info("ingest worker started")
    while True:
        try:
            task = await dequeue(timeout=5)
            if task is None:
                continue
            await process(task)
        except Exception as e:  # noqa: BLE001
            logger.error(f"worker error: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    from core.logging import configure_logging

    configure_logging()
    try:
        asyncio.run(main_loop())
    finally:
        asyncio.run(close_redis())

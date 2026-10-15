"""
文本切分：按字符滑动窗口切分，保留 chunk 重叠以减少边界信息丢失
"""
from __future__ import annotations


def split_text(text: str, chunk_size: int = 500, chunk_overlap: int = 80) -> list[str]:
    text = text.strip()
    if not text:
        return []
    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []
    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
    return chunks

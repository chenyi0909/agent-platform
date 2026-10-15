"""
文档解析器：将上传文件转为纯文本
- 当前支持 txt/md/json/csv（直接解码）
- 二进制格式（PDF/DOCX）需额外依赖，这里做 best-effort 解码并留扩展点
"""
from __future__ import annotations

from core.logging import get_logger

logger = get_logger("ingest.parser")

_TEXT_EXT = {".txt", ".md", ".markdown", ".json", ".csv", ".log", ".py", ".go", ".java", ".ts"}


class BaseParser:
    ext: set[str] = set()

    def parse(self, filename: str, data: bytes) -> str:
        raise NotImplementedError


class TextParser(BaseParser):
    ext = _TEXT_EXT

    def parse(self, filename: str, data: bytes) -> str:
        for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore")


_REGISTRY: dict[str, BaseParser] = {}


def register(p: BaseParser) -> None:
    for e in p.ext:
        _REGISTRY[e] = p


register(TextParser())


def parse_upload(filename: str, data: bytes) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    parser = _REGISTRY.get(ext, TextParser())
    return parser.parse(filename, data)

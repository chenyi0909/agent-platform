"""
结构化日志 + 全链路 trace_id
通过 contextvars 在请求/任务上下文中透传 trace_id。
"""
from __future__ import annotations

import contextvars
import logging
import sys
import uuid

from core.config import settings

trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


class TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_ctx.get()
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = (
        '{"ts":"%(asctime)s","level":"%(levelname)s",'
        '"trace_id":"%(trace_id)s","logger":"%(name)s","msg":"%(message)s"}'
    )
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.LOG_LEVEL)
    root.addFilter(TraceFilter())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

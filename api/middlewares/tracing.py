"""全链路 trace_id 中间件：每个请求分配 trace_id 并写入日志上下文"""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware

from core.logging import new_trace_id, trace_id_ctx


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tid = request.headers.get("X-Trace-Id") or new_trace_id()
        token = trace_id_ctx.set(tid)
        request.state.trace_id = tid
        start = time.time()
        try:
            response = await call_next(request)
        finally:
            trace_id_ctx.reset(token)
        response.headers["X-Trace-Id"] = tid
        response.headers["X-Process-Time"] = f"{time.time() - start:.3f}"
        return response

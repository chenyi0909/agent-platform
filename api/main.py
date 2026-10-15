"""API 服务入口"""
from __future__ import annotations

import uvicorn

from api.app import app
from core.config import settings


def main() -> None:
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

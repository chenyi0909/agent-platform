FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖（pymilvus / 编译无需，但 ssl 等需基础库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

# 等待依赖服务就绪的轻量脚本
COPY docker/wait_for_deps.sh /app/docker/wait_for_deps.sh
RUN chmod +x /app/docker/wait_for_deps.sh

EXPOSE 8000

# 容器默认启动 API 服务；ingest worker 通过 command 覆盖
CMD ["sh", "-c", "python -m api.main"]

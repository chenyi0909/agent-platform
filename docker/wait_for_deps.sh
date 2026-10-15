#!/bin/sh
# 等待依赖服务端口就绪后再启动主进程
wait_for() {
  local host="$1" port="$2" svc="$3"
  echo "waiting for $svc ($host:$port)..."
  while ! (exec 3<>/dev/tcp/$host/$port) 2>/dev/null; do
    sleep 1
  done
  exec 3>&- 2>/dev/null
  echo "$svc is up"
}

wait_for "${MYSQL_HOST:-mysql}" "${MYSQL_PORT:-3306}" mysql
wait_for "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}" redis
wait_for "${MILVUS_HOST:-milvus}" "${MILVUS_PORT:-19530}" milvus
wait_for "${ES_HOST_NAME:-elasticsearch}" 9200 elasticsearch

echo "all dependencies ready, starting: $*"
exec "$@"

#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-kriterion}" -q; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Waiting for Redis..."
until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis is ready."

echo "Waiting for Milvus..."
until curl -sf "http://${MILVUS_HOST:-milvus}:${MILVUS_PORT:-19530}/v2/health" > /dev/null 2>&1; do
  sleep 2
done
echo "Milvus is ready."

echo "Starting application..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

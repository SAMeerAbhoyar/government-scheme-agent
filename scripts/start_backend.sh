#!/usr/bin/env bash
set -e

# Script is run from inside the backend/ folder
PORT="${PORT:-8000}"

echo "==> Running Alembic migrations..."
alembic upgrade head

echo "==> Seeding database..."
python -m app.seed_demo

echo "==> Starting Uvicorn server on port ${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"

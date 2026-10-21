#!/bin/sh
# Carrega as bases (idempotente) e sobe a API.
set -e
python -m app.ingestion
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

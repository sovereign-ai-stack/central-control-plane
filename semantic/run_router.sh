#!/usr/bin/env bash
set -e

CONFIG_FILE=${1:-"config.yaml"}

echo "=================================================="
echo " Starting Enterprise Semantic Router Orchestrator..."
echo " Config: $CONFIG_FILE"
echo " Engine: FastAPI + Semantic Router + Zero-Failure RAG Probe"
echo "=================================================="

# Run the unified FastAPI Orchestrator (app.py) exposing port 8300
exec uvicorn app:app --host 0.0.0.0 --port 8300

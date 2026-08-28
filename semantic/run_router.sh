#!/usr/bin/env bash
set -e

CONFIG_FILE=${1:-"config.yaml"}

echo "=================================================="
echo " Starting vLLM Semantic Router (vllm-sr)..."
echo " Config: $CONFIG_FILE"
echo " Reference: https://github.com/vllm-project/semantic-router"
echo "=================================================="

if command -v vllm-sr &> /dev/null; then
    echo "[vllm-sr] Validating configuration..."
    vllm-sr validate --config "$CONFIG_FILE"
    echo "[vllm-sr] Starting server on port 8300..."
    exec vllm-sr serve --config "$CONFIG_FILE"
else
    echo "[fallback] vllm-sr binary not found in PATH, running FastAPI orchestrator..."
    exec uvicorn app:app --host 0.0.0.0 --port 8300
fi

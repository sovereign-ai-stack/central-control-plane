"""
Shared helpers for Weaviate-backed tests.

Integration tests run against a real local Weaviate when
`RAG_WEAVIATE_TEST_URL` is set (`host:port`, e.g. `localhost:18080`), and skip
otherwise. The default suite therefore stays fully in-memory and needs no
external service, as required.

Start one with:

    docker compose -f docker-compose.weaviate.yml up -d
"""

from __future__ import annotations

import os
import uuid

import pytest

from rag.storage.config import WeaviateConfig

ENV_URL = "RAG_WEAVIATE_TEST_URL"
ENV_GRPC = "RAG_WEAVIATE_TEST_GRPC_PORT"


def weaviate_test_endpoint() -> tuple[str, int, int] | None:
    """Return (host, http_port, grpc_port) if a test instance is configured."""
    raw = os.environ.get(ENV_URL)
    if not raw:
        return None
    value = raw.replace("http://", "").replace("https://", "").strip("/")
    host, _, port = value.partition(":")
    http_port = int(port or 8080)
    grpc_port = int(os.environ.get(ENV_GRPC, "50151"))
    return host or "localhost", http_port, grpc_port


def weaviate_available_for_tests() -> bool:
    endpoint = weaviate_test_endpoint()
    if endpoint is None:
        return False
    try:
        from rag.storage.weaviate.client import weaviate_available
    except ImportError:
        return False
    return weaviate_available()


requires_weaviate = pytest.mark.skipif(
    not weaviate_available_for_tests(),
    reason=(
        f"set {ENV_URL} (e.g. localhost:18080) and install weaviate-client to run "
        "Weaviate integration tests; start one with "
        "`docker compose -f docker-compose.weaviate.yml up -d`"
    ),
)


def unique_collection_name(prefix: str = "TestChunk") -> str:
    """A fresh collection per test module so runs cannot interfere."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def weaviate_config(collection: str, **overrides) -> WeaviateConfig:
    endpoint = weaviate_test_endpoint()
    assert endpoint is not None, "weaviate test endpoint not configured"
    host, http_port, grpc_port = endpoint
    defaults = {
        "host": host,
        "http_port": http_port,
        "grpc_port": grpc_port,
        "collection": collection,
        # Single-node dev instance: QUORUM would block.
        "consistency_level": "ONE",
        "batch_size": 50,
    }
    defaults.update(overrides)
    return WeaviateConfig(**defaults)

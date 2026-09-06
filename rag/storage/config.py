"""
Vector store configuration.

The default backend is `memory`, so nothing changes until Weaviate is explicitly
selected. Credentials are **never** read from this file: it holds only the *name*
of an environment variable, and the value is resolved at connect time. That keeps
secrets out of the repository and out of any config dump.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag.storage.errors import StorageConfigurationError

BACKEND_MEMORY = "memory"
BACKEND_WEAVIATE = "weaviate"
SUPPORTED_BACKENDS = (BACKEND_MEMORY, BACKEND_WEAVIATE)

METADATA_BACKEND_MEMORY = "memory"
METADATA_BACKEND_SQLITE = "sqlite"
SUPPORTED_METADATA_BACKENDS = (METADATA_BACKEND_MEMORY, METADATA_BACKEND_SQLITE)

DEFAULT_COLLECTION = "RagChunk"

# Guard against emitting an unbounded filter. Failing closed beyond this is
# safer than truncating an authorization filter.
DEFAULT_MAX_SCOPE_DOCUMENT_IDS = 4096


@dataclass(frozen=True, slots=True)
class WeaviateConfig:
    """Connection and behaviour settings for the Weaviate backend."""

    host: str = "localhost"
    http_port: int = 8080
    grpc_port: int = 50051
    secure: bool = False
    collection: str = DEFAULT_COLLECTION
    # Name of the env var holding the API key — never the key itself.
    api_key_env: str | None = None
    timeout_init_seconds: int = 10
    timeout_query_seconds: int = 30
    timeout_insert_seconds: int = 60
    batch_size: int = 100
    consistency_level: str = "QUORUM"
    auto_create_collection: bool = True
    auto_create_tenants: bool = True
    # Over-fetch multiplier: HNSW is approximate, so fetch more than top_k and
    # re-rank deterministically in the adapter before truncating.
    overfetch_factor: int = 4
    max_scope_document_ids: int = DEFAULT_MAX_SCOPE_DOCUMENT_IDS
    verify_model_compatibility: bool = True

    def api_key(self) -> str | None:
        """Resolve the API key from the environment at connect time."""
        if not self.api_key_env:
            return None
        value = os.environ.get(self.api_key_env)
        if not value:
            raise StorageConfigurationError(
                f"environment variable {self.api_key_env!r} is not set; "
                "it must contain the Weaviate API key"
            )
        return value

    def validate(self) -> None:
        if not self.host:
            raise StorageConfigurationError("weaviate host is required")
        if not self.collection or not self.collection[0].isupper():
            raise StorageConfigurationError(
                "weaviate collection name must be non-empty and start with an "
                "uppercase letter"
            )
        for name, value in (
            ("http_port", self.http_port),
            ("grpc_port", self.grpc_port),
            ("batch_size", self.batch_size),
            ("overfetch_factor", self.overfetch_factor),
            ("max_scope_document_ids", self.max_scope_document_ids),
        ):
            if value <= 0:
                raise StorageConfigurationError(f"{name} must be positive")
        if self.consistency_level not in {"ONE", "QUORUM", "ALL"}:
            raise StorageConfigurationError(
                "consistency_level must be one of ONE, QUORUM, ALL"
            )


@dataclass(frozen=True, slots=True)
class MetadataStoreConfig:
    """
    Durable storage for document and identity metadata.

    Defaults to `memory` so nothing changes until persistence is selected.
    `sqlite` needs no dependency; a PostgreSQL backend would add a third value
    here without touching callers.
    """

    backend: str = METADATA_BACKEND_MEMORY
    path: str = "data/rag-metadata.db"
    busy_timeout_ms: int = 5_000

    def validate(self) -> None:
        if self.backend not in SUPPORTED_METADATA_BACKENDS:
            raise StorageConfigurationError(
                f"unsupported metadata backend {self.backend!r}; "
                f"expected one of {SUPPORTED_METADATA_BACKENDS}"
            )
        if self.backend == METADATA_BACKEND_SQLITE and not self.path:
            raise StorageConfigurationError("sqlite metadata backend requires a path")
        if self.busy_timeout_ms <= 0:
            raise StorageConfigurationError("busy_timeout_ms must be positive")

    @property
    def is_persistent(self) -> bool:
        return self.backend != METADATA_BACKEND_MEMORY


@dataclass(frozen=True, slots=True)
class VectorStoreConfig:
    backend: str = BACKEND_MEMORY
    weaviate: WeaviateConfig = field(default_factory=WeaviateConfig)
    metadata: MetadataStoreConfig = field(default_factory=MetadataStoreConfig)

    def validate(self) -> None:
        if self.backend not in SUPPORTED_BACKENDS:
            raise StorageConfigurationError(
                f"unsupported vector store backend {self.backend!r}; "
                f"expected one of {SUPPORTED_BACKENDS}"
            )
        if self.backend == BACKEND_WEAVIATE:
            self.weaviate.validate()
        self.metadata.validate()

    @property
    def uses_weaviate(self) -> bool:
        return self.backend == BACKEND_WEAVIATE


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_vector_store_config(path: Path | None = None) -> VectorStoreConfig:
    config_path = path or _repo_root() / "config" / "vector_store.yaml"
    if not config_path.exists():
        return VectorStoreConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return VectorStoreConfig()
    block = raw.get("vector_store", raw)
    if not isinstance(block, dict):
        return VectorStoreConfig()
    config = _from_mapping(block)
    config.validate()
    return config


def _from_mapping(block: dict[str, Any]) -> VectorStoreConfig:
    weaviate_raw = block.get("weaviate", {})
    if not isinstance(weaviate_raw, dict):
        weaviate_raw = {}

    if "api_key" in weaviate_raw:
        raise StorageConfigurationError(
            "config must not contain 'api_key'; use 'api_key_env' naming an "
            "environment variable so secrets stay out of the repository"
        )

    weaviate_config = WeaviateConfig(
        host=str(weaviate_raw.get("host", "localhost")),
        http_port=int(weaviate_raw.get("http_port", 8080)),
        grpc_port=int(weaviate_raw.get("grpc_port", 50051)),
        secure=bool(weaviate_raw.get("secure", False)),
        collection=str(weaviate_raw.get("collection", DEFAULT_COLLECTION)),
        api_key_env=weaviate_raw.get("api_key_env"),
        timeout_init_seconds=int(weaviate_raw.get("timeout_init_seconds", 10)),
        timeout_query_seconds=int(weaviate_raw.get("timeout_query_seconds", 30)),
        timeout_insert_seconds=int(weaviate_raw.get("timeout_insert_seconds", 60)),
        batch_size=int(weaviate_raw.get("batch_size", 100)),
        consistency_level=str(weaviate_raw.get("consistency_level", "QUORUM")),
        auto_create_collection=bool(weaviate_raw.get("auto_create_collection", True)),
        auto_create_tenants=bool(weaviate_raw.get("auto_create_tenants", True)),
        overfetch_factor=int(weaviate_raw.get("overfetch_factor", 4)),
        max_scope_document_ids=int(
            weaviate_raw.get("max_scope_document_ids", DEFAULT_MAX_SCOPE_DOCUMENT_IDS)
        ),
        verify_model_compatibility=bool(
            weaviate_raw.get("verify_model_compatibility", True)
        ),
    )
    metadata_raw = block.get("metadata", {})
    if not isinstance(metadata_raw, dict):
        metadata_raw = {}
    metadata_config = MetadataStoreConfig(
        backend=str(metadata_raw.get("backend", METADATA_BACKEND_MEMORY)),
        path=str(metadata_raw.get("path", "data/rag-metadata.db")),
        busy_timeout_ms=int(metadata_raw.get("busy_timeout_ms", 5_000)),
    )

    return VectorStoreConfig(
        backend=str(block.get("backend", BACKEND_MEMORY)),
        weaviate=weaviate_config,
        metadata=metadata_config,
    )

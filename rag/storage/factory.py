"""
Chunk store selection.

The one place that decides which backend is in use. Everything else depends on
the `ChunkStore` protocol, so switching backends is a configuration change.

The Weaviate module is imported lazily: the in-memory backend, and therefore the
whole default test suite, must keep working with no client library installed.
"""

from __future__ import annotations

from rag.storage.chunk_store import ChunkStore, InMemoryChunkStore
from rag.storage.config import (
    BACKEND_MEMORY,
    BACKEND_WEAVIATE,
    METADATA_BACKEND_MEMORY,
    METADATA_BACKEND_SQLITE,
    MetadataStoreConfig,
    VectorStoreConfig,
    load_vector_store_config,
)
from rag.storage.errors import StorageConfigurationError


def create_chunk_store(config: VectorStoreConfig | None = None) -> ChunkStore:
    """Build the chunk store named by `config.backend`."""
    resolved = config or load_vector_store_config()
    resolved.validate()

    if resolved.backend == BACKEND_MEMORY:
        return InMemoryChunkStore()
    if resolved.backend == BACKEND_WEAVIATE:
        from rag.storage.weaviate.store import WeaviateChunkStore

        return WeaviateChunkStore(resolved.weaviate)
    raise StorageConfigurationError(
        f"unsupported vector store backend {resolved.backend!r}"
    )


def close_chunk_store(store: ChunkStore) -> None:
    """Release backend resources if the implementation holds any."""
    close = getattr(store, "close", None)
    if callable(close):
        close()


def create_metadata_database(config: MetadataStoreConfig):
    """
    Open the shared metadata database, or None for the in-memory backend.

    Document and identity data live in one database so a single connection and
    one set of migrations serve both.
    """
    config.validate()
    if config.backend != METADATA_BACKEND_SQLITE:
        return None

    from rag.identity.sqlite_store import MIGRATIONS as IDENTITY_MIGRATIONS
    from rag.ingestion.store.sqlite_document_store import (
        MIGRATIONS as DOCUMENT_MIGRATIONS,
    )
    from rag.storage.db import SqliteDatabase

    return SqliteDatabase(
        config.path,
        migrations=(*DOCUMENT_MIGRATIONS, *IDENTITY_MIGRATIONS),
        busy_timeout_ms=config.busy_timeout_ms,
    )


def create_document_store(config: MetadataStoreConfig | None = None, *, database=None):
    """Build the document store named by `config.backend`."""
    resolved = config or MetadataStoreConfig()
    resolved.validate()
    if resolved.backend == METADATA_BACKEND_MEMORY:
        from rag.ingestion.store.document_store import InMemoryDocumentStore

        return InMemoryDocumentStore()

    from rag.ingestion.store.sqlite_document_store import SqliteDocumentStore

    return SqliteDocumentStore(database or create_metadata_database(resolved))


def create_identity_store(config: MetadataStoreConfig | None = None, *, database=None):
    """Build the identity store named by `config.backend`."""
    resolved = config or MetadataStoreConfig()
    resolved.validate()
    if resolved.backend == METADATA_BACKEND_MEMORY:
        from rag.identity.store import InMemoryIdentityStore

        return InMemoryIdentityStore()

    from rag.identity.sqlite_store import SqliteIdentityStore

    return SqliteIdentityStore(database or create_metadata_database(resolved))


def create_permission_registry(
    config: MetadataStoreConfig | None = None, *, database=None
):
    """Build the ingest permission registry named by `config.backend`."""
    resolved = config or MetadataStoreConfig()
    resolved.validate()
    if resolved.backend == METADATA_BACKEND_MEMORY:
        from rag.ingestion.authz import IngestPermissionRegistry

        return IngestPermissionRegistry()

    from rag.identity.sqlite_store import SqlitePermissionRegistry

    return SqlitePermissionRegistry(database or create_metadata_database(resolved))

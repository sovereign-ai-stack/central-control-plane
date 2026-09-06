"""Weaviate-backed chunk storage."""

from rag.storage.weaviate.client import connect, weaviate_available
from rag.storage.weaviate.mapping import (
    chunk_to_properties,
    chunk_to_vector,
    distance_to_similarity,
    properties_to_chunk,
    vector_from_object,
)
from rag.storage.weaviate.schema import ensure_collection, tenant_name
from rag.storage.weaviate.store import WeaviateChunkStore

__all__ = [
    "WeaviateChunkStore",
    "chunk_to_properties",
    "chunk_to_vector",
    "connect",
    "distance_to_similarity",
    "ensure_collection",
    "properties_to_chunk",
    "tenant_name",
    "vector_from_object",
    "weaviate_available",
]

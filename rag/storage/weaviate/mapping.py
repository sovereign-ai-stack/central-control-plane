"""
Translation between `StoredChunk` and Weaviate objects.

Kept free of client imports so the mapping is unit-testable without a running
Weaviate or even the client library installed.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import numpy as np

from rag.ingestion.types import StoredChunk
from rag.storage.errors import StorageWriteError
from rag.storage.weaviate.schema import (
    PROP_CHAR_END,
    PROP_CHAR_START,
    PROP_CHUNK_ID,
    PROP_CHUNK_INDEX,
    PROP_COMPANY_ID,
    PROP_CONTENT,
    PROP_CONTENT_HASH,
    PROP_DEPARTMENT_ID,
    PROP_DOCUMENT_ID,
    PROP_DOCUMENT_STATUS,
    PROP_DOCUMENT_VERSION,
    PROP_EMBEDDING_DIMENSION,
    PROP_EMBEDDING_MODEL_ID,
    PROP_EMBEDDING_TEXT,
    PROP_LANGUAGE,
    PROP_NLP_VERSION,
    PROP_ORIGINAL_TEXT,
    PROP_SECTION_PATH,
    PROP_SOURCE_SEGMENT_END,
    PROP_SOURCE_SEGMENT_LABEL,
    PROP_SOURCE_SEGMENT_START,
    PROP_TOKEN_COUNT,
)


def chunk_to_properties(chunk: StoredChunk) -> dict[str, Any]:
    """Flatten a chunk into Weaviate properties, omitting unset optionals."""
    properties: dict[str, Any] = {
        PROP_CHUNK_ID: str(chunk.chunk_id),
        PROP_DOCUMENT_ID: str(chunk.document_id),
        PROP_COMPANY_ID: str(chunk.company_id),
        PROP_DEPARTMENT_ID: str(chunk.department_id),
        PROP_DOCUMENT_VERSION: int(chunk.document_version),
        PROP_CHUNK_INDEX: int(chunk.chunk_index),
        PROP_CONTENT: chunk.content,
        PROP_CONTENT_HASH: chunk.content_hash,
        PROP_EMBEDDING_MODEL_ID: chunk.embedding_model_id,
        PROP_EMBEDDING_DIMENSION: int(chunk.embedding_dimension or 0),
    }
    optional = {
        PROP_TOKEN_COUNT: chunk.token_count,
        PROP_ORIGINAL_TEXT: chunk.original_text,
        PROP_EMBEDDING_TEXT: chunk.embedding_text,
        PROP_NLP_VERSION: chunk.nlp_version,
        PROP_LANGUAGE: chunk.language,
        PROP_SECTION_PATH: chunk.section_path,
        PROP_CHAR_START: chunk.char_start,
        PROP_CHAR_END: chunk.char_end,
        PROP_SOURCE_SEGMENT_LABEL: chunk.source_segment_label,
        PROP_SOURCE_SEGMENT_START: chunk.source_segment_start,
        PROP_SOURCE_SEGMENT_END: chunk.source_segment_end,
        PROP_DOCUMENT_STATUS: chunk.document_status,
    }
    for key, value in optional.items():
        if value is not None:
            properties[key] = value
    return properties


def chunk_to_vector(chunk: StoredChunk) -> list[float]:
    if chunk.embedding is None:
        raise StorageWriteError("chunk is missing its embedding vector")
    return [float(value) for value in chunk.embedding]


def properties_to_chunk(
    properties: dict[str, Any],
    *,
    embedding: np.ndarray | None = None,
) -> StoredChunk:
    """Rebuild a `StoredChunk` from stored properties."""
    return StoredChunk(
        chunk_id=_uuid(properties, PROP_CHUNK_ID),
        document_id=_uuid(properties, PROP_DOCUMENT_ID),
        company_id=_uuid(properties, PROP_COMPANY_ID),
        department_id=_uuid(properties, PROP_DEPARTMENT_ID),
        document_version=_int(properties.get(PROP_DOCUMENT_VERSION), default=1),
        chunk_index=_int(properties.get(PROP_CHUNK_INDEX), default=0),
        content=str(properties.get(PROP_CONTENT) or ""),
        content_hash=str(properties.get(PROP_CONTENT_HASH) or ""),
        embedding=embedding,
        embedding_model_id=_optional_str(properties.get(PROP_EMBEDDING_MODEL_ID)),
        embedding_dimension=_optional_int(properties.get(PROP_EMBEDDING_DIMENSION)),
        token_count=_optional_int(properties.get(PROP_TOKEN_COUNT)),
        original_text=_optional_str(properties.get(PROP_ORIGINAL_TEXT)),
        embedding_text=_optional_str(properties.get(PROP_EMBEDDING_TEXT)),
        nlp_version=_optional_str(properties.get(PROP_NLP_VERSION)),
        language=_optional_str(properties.get(PROP_LANGUAGE)),
        section_path=_optional_str(properties.get(PROP_SECTION_PATH)),
        char_start=_optional_int(properties.get(PROP_CHAR_START)),
        char_end=_optional_int(properties.get(PROP_CHAR_END)),
        source_segment_label=_optional_str(properties.get(PROP_SOURCE_SEGMENT_LABEL)),
        source_segment_start=_optional_int(properties.get(PROP_SOURCE_SEGMENT_START)),
        source_segment_end=_optional_int(properties.get(PROP_SOURCE_SEGMENT_END)),
        document_status=_optional_str(properties.get(PROP_DOCUMENT_STATUS)),
    )


def distance_to_similarity(distance: float | None) -> float:
    """
    Convert Weaviate cosine distance to the cosine similarity this system uses.

    Verified against a live instance: `similarity = 1 - distance` reproduces the
    dot product of L2-normalized vectors that `rank_by_similarity` expects.
    """
    if distance is None:
        return 0.0
    return 1.0 - float(distance)


def vector_from_object(raw: Any) -> np.ndarray | None:
    """Normalize the client's vector representation into a float32 array."""
    if raw is None:
        return None
    values = raw
    if isinstance(raw, dict):
        values = raw.get("default")
        if values is None:
            values = next(iter(raw.values()), None)
    if values is None:
        return None
    return np.asarray(values, dtype=np.float32)


def _uuid(properties: dict[str, Any], key: str) -> UUID:
    value = properties.get(key)
    if value is None:
        raise StorageWriteError(f"stored object is missing required property {key!r}")
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    return int(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None

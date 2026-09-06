from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

import numpy as np


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    DELETED = "deleted"


NORMALIZATION_VERSION = "fa-norm-v1"


@dataclass(frozen=True, slots=True)
class IngestDocumentRequest:
    content: str
    company_id: UUID
    department_id: UUID
    source: str
    document_id: UUID | None = None
    title: str | None = None
    language: str = "fa"
    source_type: str = "api"
    source_uri: str | None = None
    deduplicate: bool = False


@dataclass(frozen=True, slots=True)
class IngestFileRequest:
    """
    Ingest a document from raw file bytes of any supported format.

    `source_type` is an optional declaration; when omitted the extractor
    registry sniffs the content. Callers never choose the parser directly.
    """

    data: bytes
    company_id: UUID
    department_id: UUID
    source: str
    filename: str | None = None
    source_type: str | None = None
    document_id: UUID | None = None
    title: str | None = None
    language: str = "fa"
    source_uri: str | None = None
    deduplicate: bool = False


@dataclass(frozen=True, slots=True)
class IngestDocumentUpdateRequest:
    content: str
    company_id: UUID
    department_id: UUID
    source: str | None = None
    title: str | None = None
    language: str = "fa"


@dataclass(frozen=True, slots=True)
class IngestScope:
    company_id: UUID
    department_id: UUID
    actor_user_id: UUID


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    chunk_index: int
    content: str
    char_start: int
    char_end: int


@dataclass(frozen=True, slots=True)
class StoredChunk:
    """
    A persisted chunk.

    `content` is the normalized text: it is what retrieval returns, what the
    lexical scorer matches, and what citations quote. The Phase 5 enrichment
    fields are all optional and appended, so chunks written before Phase 5 stay
    valid and existing callers are unaffected.

    `original_text` preserves the pre-normalization source and `embedding_text`
    records the representation actually sent to the embedding model — improving
    semantic retrieval must not mean losing the source text.
    """

    chunk_id: UUID
    document_id: UUID
    company_id: UUID
    department_id: UUID
    document_version: int
    chunk_index: int
    content: str
    content_hash: str
    embedding: np.ndarray | None = None
    embedding_model_id: str | None = None
    embedding_dimension: int | None = None
    token_count: int | None = None
    original_text: str | None = None
    embedding_text: str | None = None
    nlp_version: str | None = None
    language: str | None = None
    section_path: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    source_segment_label: str | None = None
    source_segment_start: int | None = None
    source_segment_end: int | None = None
    # Denormalised document status so the vector store can filter searchability
    # server-side instead of the engine scanning every document per query.
    # Only INDEXED chunks are searchable; anything else fails closed.
    document_status: str | None = None

    @property
    def text_for_embedding(self) -> str:
        """Representation to embed: the processed form when present."""
        return self.embedding_text or self.content


@dataclass
class DocumentRecord:
    id: UUID
    company_id: UUID
    department_id: UUID
    source: str
    language: str
    source_type: str
    version: int
    status: DocumentStatus
    content_hash: str
    normalization_version: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    source_uri: str | None = None
    indexed_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class IngestDocumentResponse:
    document_id: UUID
    status: DocumentStatus
    version: int
    chunk_count: int
    content_hash: str
    deduplicated: bool = False
    http_status: int = 202


@dataclass
class AuditEvent:
    name: str
    request_id: UUID
    fields: dict[str, object] = field(default_factory=dict)

"""
Ingestion pipeline orchestration — chunking, embedding, and persistence.

Phase 5 flow:

    ExtractedDocument -> Persian NLP normalization -> adaptive chunking
                      -> metadata enrichment -> EmbeddingService -> ChunkStore

Backward compatibility: with no chunker, NLP pipeline, or extraction provenance
supplied, this behaves exactly as it did before Phase 5 — fa-norm-v1
normalization and character-budget chunking — so stored content hashes and
existing corpora are unaffected.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from uuid import UUID

from rag.embedding.service import EmbeddingService
from rag.ingestion.audit import IngestAuditLog
from rag.ingestion.chunking import ChunkingStrategy, FixedCharChunker
from rag.ingestion.embedding_integration import embed_and_attach_chunks
from rag.ingestion.errors import IngestPipelineError
from rag.ingestion.extraction.types import SourceSegment
from rag.ingestion.metadata import build_stored_chunks
from rag.ingestion.persian import normalization_version, normalize_persian
from rag.ingestion.source_position import normalize_segments
from rag.ingestion.store.document_store import DocumentStore
from rag.ingestion.types import (
    DocumentRecord,
    DocumentStatus,
    IngestDocumentRequest,
    IngestScope,
    StoredChunk,
)
from rag.ingestion.validation import content_hash
from rag.nlp.pipeline import PersianNlpPipeline
from rag.storage.chunk_store import ChunkStore


class IngestionPipeline:
    def __init__(
        self,
        document_store: DocumentStore,
        chunk_store: ChunkStore,
        embedding_service: EmbeddingService,
        audit_log: IngestAuditLog | None = None,
        *,
        chunker: ChunkingStrategy | None = None,
        nlp: PersianNlpPipeline | None = None,
    ) -> None:
        self._documents = document_store
        self._chunks = chunk_store
        self._embedding = embedding_service
        self._audit = audit_log or IngestAuditLog()
        self._chunker = chunker or FixedCharChunker()
        self._nlp = nlp if (nlp is not None and nlp.config.enabled) else None

    @property
    def audit_log(self) -> IngestAuditLog:
        return self._audit

    @property
    def chunker(self) -> ChunkingStrategy:
        return self._chunker

    @property
    def nlp(self) -> PersianNlpPipeline | None:
        return self._nlp

    @property
    def normalization_version(self) -> str:
        return (
            self._nlp.config.normalization_version
            if self._nlp is not None
            else normalization_version()
        )

    def normalize(self, text: str) -> str:
        """Document-level normalization: fa-norm-v2 when the NLP layer is on."""
        return self._nlp.normalize(text) if self._nlp is not None else normalize_persian(text)

    def process_create(
        self,
        request: IngestDocumentRequest,
        scope: IngestScope,
        request_id: UUID,
        *,
        segments: Sequence[SourceSegment] = (),
    ) -> tuple[DocumentRecord, list[StoredChunk]]:
        normalized, normalized_segments = self._normalize_document(
            request.content, segments
        )
        doc_hash = content_hash(normalized)
        document = self._documents.create_processing(
            company_id=scope.company_id,
            department_id=scope.department_id,
            source=request.source,
            language=request.language,
            source_type=request.source_type,
            content_hash=doc_hash,
            normalization_version=self.normalization_version,
            document_id=request.document_id,
            title=request.title,
            source_uri=request.source_uri,
        )
        try:
            chunks = self._build_and_persist(
                document,
                normalized,
                segments=normalized_segments,
                original_text=request.content,
                language=request.language,
            )
        except Exception as exc:
            self._documents.mark_failed(document.id, str(exc.__class__.__name__))
            self._chunks.delete_by_document_id(document.id)
            self._audit.emit(
                "ingestion.failed",
                request_id,
                document_id=document.id,
                failure_reason=str(exc.__class__.__name__),
            )
            raise IngestPipelineError(str(exc)) from exc

        indexed = self._documents.mark_indexed(
            document.id,
            chunk_count=len(chunks),
            content_hash=doc_hash,
        )
        self._publish(document.id)
        self._audit.emit(
            "ingestion.completed",
            request_id,
            document_id=indexed.id,
            company_id=indexed.company_id,
            department_id=indexed.department_id,
            chunk_count=indexed.chunk_count,
        )
        return indexed, chunks

    def process_update(
        self,
        document: DocumentRecord,
        content: str,
        request_id: UUID,
        *,
        segments: Sequence[SourceSegment] = (),
    ) -> tuple[DocumentRecord, list[StoredChunk]]:
        normalized, normalized_segments = self._normalize_document(content, segments)
        doc_hash = content_hash(normalized)
        prior_chunk_count = document.chunk_count
        prior_content_hash = document.content_hash
        prior_version = document.version
        # Hide the current chunks before rewriting them, so a partially
        # rewritten document is never searchable mid-flight.
        self._unpublish(document.id)
        self._documents.begin_reindex(document.id, doc_hash)
        new_version = document.version + 1
        try:
            working = self._documents.get(document.id)
            assert working is not None
            chunks = self._build_and_persist(
                replace(working, version=new_version),
                normalized,
                segments=normalized_segments,
                original_text=content,
                language=working.language,
            )
        except Exception as exc:
            self._documents.mark_indexed(
                document.id,
                chunk_count=prior_chunk_count,
                content_hash=prior_content_hash,
                version=prior_version,
            )
            # Restore visibility too: the document is INDEXED again, so leaving
            # its chunks hidden would silently make healthy content unreachable.
            self._publish(document.id)
            self._audit.emit(
                "ingestion.failed",
                request_id,
                document_id=document.id,
                failure_reason=str(exc.__class__.__name__),
            )
            raise IngestPipelineError(str(exc)) from exc

        indexed = self._documents.mark_indexed(
            document.id,
            chunk_count=len(chunks),
            content_hash=doc_hash,
            version=new_version,
        )
        self._publish(document.id)
        self._audit.emit(
            "ingestion.completed",
            request_id,
            document_id=indexed.id,
            company_id=indexed.company_id,
            department_id=indexed.department_id,
            chunk_count=indexed.chunk_count,
        )
        return indexed, chunks

    def _publish(self, document_id: UUID) -> None:
        """
        Make a document's chunks searchable.

        This is the commit point for visibility. Failures propagate: a document
        that silently stayed hidden would be a silent data-loss bug.
        """
        self._chunks.set_document_status(document_id, DocumentStatus.INDEXED.value)

    def _unpublish(self, document_id: UUID) -> None:
        """Hide a document's chunks. Fails closed — content stays hidden."""
        self._chunks.set_document_status(document_id, DocumentStatus.PROCESSING.value)

    def _normalize_document(
        self,
        content: str,
        segments: Sequence[SourceSegment],
    ) -> tuple[str, tuple[SourceSegment, ...]]:
        """
        Normalize the document, keeping segment offsets aligned.

        Segments are normalized individually and rejoined so their offsets index
        the normalized text; normalization changes string length, so reusing the
        extracted-text offsets would mis-attribute chunk provenance.
        """
        if not segments:
            return self.normalize(content), ()
        return normalize_segments(segments, content, self.normalize)

    def _build_and_persist(
        self,
        document: DocumentRecord,
        normalized_content: str,
        *,
        segments: Sequence[SourceSegment] = (),
        original_text: str | None = None,
        language: str | None = None,
    ) -> list[StoredChunk]:
        drafts = self._chunker.split(normalized_content)
        if not drafts:
            raise IngestPipelineError("no chunks produced from content")
        chunks = build_stored_chunks(
            drafts,
            document_id=document.id,
            company_id=document.company_id,
            department_id=document.department_id,
            document_version=document.version,
            nlp=self._nlp,
            segments=segments,
            language=language,
            original_text=original_text,
        )
        chunks = embed_and_attach_chunks(self._embedding, chunks)
        self._chunks.replace_document_chunks(document.id, chunks)
        if self._chunks.count_by_document_id(document.id) != len(chunks):
            raise IngestPipelineError("chunk persistence count mismatch")
        return chunks

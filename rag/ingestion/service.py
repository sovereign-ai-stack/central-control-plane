"""Ingestion service — create, update, delete."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from rag.app.rate_limit import RateLimiter
from rag.authorization.context import AuthorizationContext
from rag.authorization.errors import ClientScopeForgeryError
from rag.identity.errors import IdentityError
from rag.identity.resolver import IdentityResolutionService
from rag.identity.types import RagRetrieveRequest
from rag.ingestion.authz import IngestAuthorizationService
from rag.ingestion.errors import (
    IngestAuthzDeniedError,
    IngestDuplicateError,
    IngestNotFoundError,
    IngestUnauthorizedError,
    IngestValidationError,
)
from rag.ingestion.extraction.errors import ExtractionError
from rag.ingestion.extraction.registry import ExtractorRegistry
from rag.ingestion.extraction.types import ExtractedDocument, SourceSegment
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.store.document_store import DocumentStore
from rag.ingestion.types import (
    DocumentStatus,
    IngestDocumentRequest,
    IngestDocumentResponse,
    IngestDocumentUpdateRequest,
    IngestFileRequest,
    IngestScope,
)
from rag.ingestion.validation import content_hash, validate_create_request, validate_update_request
from rag.storage.chunk_store import ChunkStore


class IngestionService:
    def __init__(
        self,
        identity_service: IdentityResolutionService,
        authz_service: IngestAuthorizationService,
        pipeline: IngestionPipeline,
        document_store: DocumentStore,
        chunk_store: ChunkStore,
        *,
        extractors: ExtractorRegistry | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._identity = identity_service
        self._authz = authz_service
        self._pipeline = pipeline
        self._documents = document_store
        self._chunks = chunk_store
        self._extractors = extractors or ExtractorRegistry()
        self._rate_limiter = rate_limiter

    def create_document(
        self,
        request: IngestDocumentRequest,
        request_id: UUID,
        bearer_token: str | None,
    ) -> IngestDocumentResponse:
        self._throttle(bearer_token)
        validate_create_request(request)
        authz = self._resolve_authz(request_id, bearer_token)
        scope = self._authorize_create(authz, request, request_id)
        return self._create(request, scope, request_id)

    def create_document_from_file(
        self,
        request: IngestFileRequest,
        request_id: UUID,
        bearer_token: str | None,
    ) -> IngestDocumentResponse:
        """
        Ingest a document from file bytes of any registered format.

        Authorization is resolved **before** extraction, mirroring the retrieval
        rule that identity precedes embedding: an unauthenticated or
        unauthorized caller must never reach a document parser.
        """
        # Throttle before extraction: parsing an uploaded file is the most
        # expensive thing an unauthenticated-adjacent caller can trigger.
        self._throttle(bearer_token)
        self._validate_file_request(request)
        authz = self._resolve_authz(request_id, bearer_token)
        scope = self._authorize_create_scope(
            authz, request.company_id, request.department_id, request_id
        )

        extracted = self._extract(request, request_id, authz.user_id)
        document_request = IngestDocumentRequest(
            content=extracted.text,
            company_id=request.company_id,
            department_id=request.department_id,
            source=request.source,
            document_id=request.document_id,
            title=request.title or extracted.metadata.get("title"),
            language=request.language,
            source_type=extracted.source_type,
            source_uri=request.source_uri,
            deduplicate=request.deduplicate,
        )
        validate_create_request(document_request)
        return self._create(
            document_request, scope, request_id, segments=extracted.segments
        )

    def _throttle(self, bearer_token: str | None) -> None:
        if self._rate_limiter is not None:
            self._rate_limiter.enforce(bearer_token, scope="ingest")

    def _extract(
        self,
        request: IngestFileRequest,
        request_id: UUID,
        actor_id: UUID,
    ) -> ExtractedDocument:
        try:
            return self._extractors.extract(
                request.data,
                filename=request.filename,
                source_type=request.source_type,
            )
        except ExtractionError as exc:
            self._pipeline.audit_log.emit(
                "ingestion.rejected",
                request_id,
                reason=exc.__class__.__name__,
                actor_id=actor_id,
            )
            raise

    def _create(
        self,
        request: IngestDocumentRequest,
        scope: IngestScope,
        request_id: UUID,
        *,
        segments: Sequence[SourceSegment] = (),
    ) -> IngestDocumentResponse:
        # Hash with the same normalizer the pipeline persists with, so the
        # dedup key and the stored content hash can never disagree.
        normalized = self._pipeline.normalize(request.content)
        doc_hash = content_hash(normalized)

        if request.deduplicate:
            existing = self._documents.find_indexed_by_content_hash(
                request.company_id, request.department_id, doc_hash
            )
            if existing is not None:
                return IngestDocumentResponse(
                    document_id=existing.id,
                    status=existing.status,
                    version=existing.version,
                    chunk_count=existing.chunk_count,
                    content_hash=existing.content_hash,
                    deduplicated=True,
                    http_status=200,
                )

        duplicate = self._documents.find_indexed_by_content_hash(
            request.company_id, request.department_id, doc_hash
        )
        if duplicate is not None and not request.deduplicate:
            raise IngestDuplicateError(
                f"duplicate content exists for document {duplicate.id}"
            )

        document, _ = self._pipeline.process_create(
            request, scope, request_id, segments=segments
        )
        return IngestDocumentResponse(
            document_id=document.id,
            status=document.status,
            version=document.version,
            chunk_count=document.chunk_count,
            content_hash=document.content_hash,
            http_status=202,
        )

    @staticmethod
    def _validate_file_request(request: IngestFileRequest) -> None:
        if not request.data:
            raise IngestValidationError("file content is required")
        if not request.source or not request.source.strip():
            raise IngestValidationError("source is required")

    def update_document(
        self,
        document_id: UUID,
        request: IngestDocumentUpdateRequest,
        request_id: UUID,
        bearer_token: str | None,
    ) -> IngestDocumentResponse:
        validate_update_request(request)
        authz = self._resolve_authz(request_id, bearer_token)

        document = self._documents.get(document_id)
        if document is None or document.status == DocumentStatus.DELETED:
            raise IngestNotFoundError(f"document not found: {document_id}")

        self._authz.authorize_document_access(authz, document)
        self._authz.assert_scope_unchanged(
            document, request.company_id, request.department_id
        )

        document, _ = self._pipeline.process_update(document, request.content, request_id)
        return IngestDocumentResponse(
            document_id=document.id,
            status=document.status,
            version=document.version,
            chunk_count=document.chunk_count,
            content_hash=document.content_hash,
            http_status=202,
        )

    def delete_document(
        self,
        document_id: UUID,
        request_id: UUID,
        bearer_token: str | None,
    ) -> None:
        authz = self._resolve_authz(request_id, bearer_token)
        document = self._documents.get(document_id)
        if document is None or document.status == DocumentStatus.DELETED:
            raise IngestNotFoundError(f"document not found: {document_id}")

        self._authz.authorize_document_access(authz, document)
        self._chunks.delete_by_document_id(document_id)
        self._documents.mark_deleted(document_id)
        self._pipeline.audit_log.emit(
            "ingestion.deleted",
            request_id,
            document_id=document_id,
        )

    def _resolve_authz(
        self, request_id: UUID, bearer_token: str | None
    ) -> AuthorizationContext:
        if not bearer_token:
            self._pipeline.audit_log.emit(
                "ingestion.rejected", request_id, reason="missing_authentication"
            )
            raise IngestUnauthorizedError("Authentication required")
        try:
            return self._identity.resolve_authorization(
                RagRetrieveRequest(request_id=request_id),
                bearer_token=bearer_token,
            )
        except IdentityError as exc:
            self._pipeline.audit_log.emit(
                "ingestion.rejected", request_id, reason=exc.__class__.__name__
            )
            if exc.http_status == 403:
                raise IngestAuthzDeniedError(str(exc)) from exc
            raise IngestUnauthorizedError(str(exc)) from exc

    def _authorize_create(
        self,
        authz: AuthorizationContext,
        request: IngestDocumentRequest,
        request_id: UUID,
    ):
        return self._authorize_create_scope(
            authz, request.company_id, request.department_id, request_id
        )

    def _authorize_create_scope(
        self,
        authz: AuthorizationContext,
        company_id: UUID,
        department_id: UUID,
        request_id: UUID,
    ):
        try:
            return self._authz.authorize_create_scope(authz, company_id, department_id)
        except (IngestAuthzDeniedError, ClientScopeForgeryError, IngestValidationError) as exc:
            self._pipeline.audit_log.emit(
                "ingestion.rejected",
                request_id,
                reason=exc.__class__.__name__,
                actor_id=authz.user_id,
            )
            raise

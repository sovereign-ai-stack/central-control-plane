"""
Security regression tests for file ingestion (Phase 5A/5B).

File upload is new attack surface. The invariants asserted here:

- authorization is resolved *before* any parser touches the bytes
- resource limits are enforced, so a hostile file cannot exhaust memory
- malformed files produce typed client errors, never 5xx or parser internals
- tenant isolation and enrichment metadata leak nothing across companies
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from rag.authorization.errors import ClientScopeForgeryError
from rag.ingestion.errors import (
    IngestAuthzDeniedError,
    IngestUnauthorizedError,
    IngestValidationError,
)
from rag.ingestion.extraction.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    ExtractionError,
    ExtractionLimitError,
    UnsupportedSourceTypeError,
)
from rag.ingestion.extraction.limits import ExtractionLimits
from rag.ingestion.extraction.registry import ExtractorRegistry, default_extractors
from rag.ingestion.service import IngestionService
from rag.ingestion.types import IngestFileRequest
from tests.rag.pdf_fixtures import (
    build_corrupt_pdf,
    build_encrypted_pdf,
    build_image_only_pdf,
    build_pdf,
)


class CountingExtractorRegistry(ExtractorRegistry):
    """Registry that records whether extraction was ever attempted."""

    def __init__(self, limits: ExtractionLimits | None = None) -> None:
        super().__init__(default_extractors(limits))
        self.extract_calls = 0

    def extract(self, data, *, filename=None, source_type=None):
        self.extract_calls += 1
        return super().extract(data, filename=filename, source_type=source_type)


@pytest.fixture
def counting_ingestion(rag_application, ingest_permissions):
    from rag.identity.provider import StoreIdentityProvider
    from rag.ingestion.authz import IngestAuthorizationService

    registry = CountingExtractorRegistry()
    provider = StoreIdentityProvider(rag_application.identity_store)
    service = IngestionService(
        rag_application.identity_service,
        IngestAuthorizationService(provider, ingest_permissions),
        rag_application.ingestion_service._pipeline,
        rag_application.document_store,
        rag_application.chunk_store,
        extractors=registry,
    )
    return service, registry


def _request(tenant_ids, data: bytes, *, company="C1", department="C1_D1", **kwargs):
    return IngestFileRequest(
        data=data,
        company_id=tenant_ids["companies"][company],
        department_id=tenant_ids["departments"][department],
        source="file-security-fixture",
        **kwargs,
    )


@pytest.mark.security
class TestAuthorizationBeforeExtraction:
    def test_unauthenticated_upload_never_reaches_the_parser(
        self, counting_ingestion, tenant_ids, request_id
    ):
        service, registry = counting_ingestion
        with pytest.raises(IngestUnauthorizedError):
            service.create_document_from_file(
                _request(tenant_ids, build_pdf(["secret"])), request_id, None
            )
        assert registry.extract_calls == 0

    def test_invalid_token_never_reaches_the_parser(
        self, counting_ingestion, tenant_ids, request_id
    ):
        service, registry = counting_ingestion
        with pytest.raises(IngestUnauthorizedError):
            service.create_document_from_file(
                _request(tenant_ids, build_pdf(["secret"])),
                request_id,
                tenant_ids["tokens"]["INVALID"],
            )
        assert registry.extract_calls == 0

    def test_cross_company_upload_never_reaches_the_parser(
        self, counting_ingestion, tenant_ids, request_id
    ):
        service, registry = counting_ingestion
        with pytest.raises((IngestAuthzDeniedError, ClientScopeForgeryError)):
            service.create_document_from_file(
                _request(tenant_ids, build_pdf(["secret"]), company="C2", department="C2_D1"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        assert registry.extract_calls == 0

    def test_unauthorized_department_never_reaches_the_parser(
        self, counting_ingestion, tenant_ids, request_id
    ):
        service, registry = counting_ingestion
        with pytest.raises(ClientScopeForgeryError):
            service.create_document_from_file(
                _request(tenant_ids, build_pdf(["secret"]), department="C1_D2"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        assert registry.extract_calls == 0

    def test_authorized_upload_does_reach_the_parser(
        self, counting_ingestion, tenant_ids, request_id
    ):
        service, registry = counting_ingestion
        service.create_document_from_file(
            _request(tenant_ids, build_pdf(["authorized content here"])),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert registry.extract_calls == 1


@pytest.mark.security
class TestResourceLimits:
    def test_oversized_file_rejected(self, tenant_ids):
        limits = ExtractionLimits(max_file_bytes=64)
        registry = ExtractorRegistry(default_extractors(limits))
        with pytest.raises(ExtractionLimitError):
            registry.extract(b"x" * 100, filename="big.txt")

    def test_page_bomb_rejected(self):
        limits = ExtractionLimits(max_pages=3)
        registry = ExtractorRegistry(default_extractors(limits))
        with pytest.raises(ExtractionLimitError):
            registry.extract(build_pdf([f"page {i}" for i in range(20)]))

    def test_extracted_text_limit_rejected(self):
        limits = ExtractionLimits(max_extracted_chars=10)
        registry = ExtractorRegistry(default_extractors(limits))
        with pytest.raises(ExtractionLimitError):
            registry.extract(("x" * 500).encode(), filename="long.txt")

    def test_limit_errors_map_to_413(self):
        assert ExtractionLimitError("x").http_status == 413


@pytest.mark.security
class TestMalformedFileHandling:
    @pytest.mark.parametrize(
        ("data", "expected"),
        [
            (build_corrupt_pdf(), CorruptDocumentError),
            (build_encrypted_pdf(), CorruptDocumentError),
            (build_image_only_pdf(), EmptyDocumentError),
            (b"", CorruptDocumentError),
        ],
    )
    def test_malformed_pdfs_raise_typed_client_errors(self, data, expected):
        registry = ExtractorRegistry()
        with pytest.raises(expected) as exc_info:
            registry.extract(data, filename="input.pdf")
        assert exc_info.value.http_status < 500

    def test_empty_untyped_upload_reports_an_empty_document(self):
        registry = ExtractorRegistry()
        with pytest.raises(EmptyDocumentError) as exc_info:
            registry.extract(b"")
        assert exc_info.value.http_status < 500

    def test_binary_garbage_is_unsupported(self):
        registry = ExtractorRegistry()
        with pytest.raises(UnsupportedSourceTypeError):
            registry.extract(b"\xff\xfe\x00\x01\x02", filename="mystery.bin")

    def test_errors_never_expose_file_content_or_parser_internals(self):
        secret = "CONFIDENTIAL-SALARY-DATA"
        registry = ExtractorRegistry()
        with pytest.raises(ExtractionError) as exc_info:
            registry.extract(
                b"%PDF-1.4\n" + secret.encode() + b"\nbroken", filename="x.pdf"
            )
        message = str(exc_info.value)
        assert secret not in message
        assert "pypdf" not in message.lower()
        assert "Traceback" not in message

    def test_empty_upload_rejected_before_parsing(
        self, rag_application, tenant_ids, request_id
    ):
        with pytest.raises(IngestValidationError):
            rag_application.ingestion_service.create_document_from_file(
                _request(tenant_ids, b""), request_id, tenant_ids["tokens"]["U1"]
            )

    def test_failed_extraction_creates_no_document(
        self, rag_application, tenant_ids, request_id
    ):
        before = rag_application.document_store.count()
        with pytest.raises(CorruptDocumentError):
            rag_application.ingestion_service.create_document_from_file(
                _request(tenant_ids, build_corrupt_pdf(), filename="bad.pdf"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )
        assert rag_application.document_store.count() == before


@pytest.mark.security
class TestTenantIsolationOnUploads:
    def test_uploaded_chunks_carry_the_authorized_scope(
        self, rag_application, tenant_ids, request_id
    ):
        response = rag_application.ingestion_service.create_document_from_file(
            _request(tenant_ids, build_pdf(["tenant scoped body"]), filename="a.pdf"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = rag_application.chunk_store.list_by_document_id(response.document_id)
        assert chunks
        for chunk in chunks:
            assert chunk.company_id == tenant_ids["companies"]["C1"]
            assert chunk.department_id == tenant_ids["departments"]["C1_D1"]

    def test_uploaded_document_not_retrievable_by_other_department(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        from rag.app.types import RetrievalApiRequest

        rag_application.ingestion_service.create_document_from_file(
            _request(
                tenant_ids,
                build_pdf(["restricted upload marker"]),
                department="C1_D2",
                filename="restricted.pdf",
                document_id=uuid4(),
            ),
            request_id,
            tenant_ids["tokens"]["S1"],
        )
        response = retrieve_handler.retrieve(
            RetrievalApiRequest(
                query="restricted upload marker", request_id=request_id, top_k=5
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunks == ()

    def test_enrichment_metadata_contains_no_cross_tenant_data(
        self, rag_application, tenant_ids, request_id
    ):
        response = rag_application.ingestion_service.create_document_from_file(
            _request(tenant_ids, build_pdf(["page one body", "page two body"])),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        other_company = str(tenant_ids["companies"]["C2"])
        for chunk in rag_application.chunk_store.list_by_document_id(
            response.document_id
        ):
            serialized = " ".join(
                str(value)
                for value in (
                    chunk.original_text,
                    chunk.embedding_text,
                    chunk.section_path,
                    chunk.source_segment_label,
                    chunk.nlp_version,
                )
            )
            assert other_company not in serialized

    def test_caller_cannot_choose_the_parser_to_bypass_limits(self, tenant_ids):
        # source_type only selects among registered adapters; it cannot smuggle
        # an arbitrary parser or disable limits.
        registry = ExtractorRegistry()
        with pytest.raises(UnsupportedSourceTypeError):
            registry.extract(b"x", source_type="../../etc/passwd")

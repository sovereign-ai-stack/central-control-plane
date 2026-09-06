"""
Integration tests for the Phase 5 ingestion flow.

    file -> extraction -> Persian NLP -> adaptive chunking
         -> metadata enrichment -> embedding -> retrieval
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from tests.rag.conftest import STUB_EMBEDDING_CONFIG, make_ingest_request
from tests.rag.pdf_fixtures import build_corrupt_pdf, build_pdf, build_persian_pdf

from rag.app.factory import RagApplication
from rag.app.types import RetrievalApiRequest
from rag.ingestion.chunking import STRATEGY_SEMANTIC, ChunkingConfig
from rag.ingestion.extraction.errors import CorruptDocumentError
from rag.ingestion.types import IngestFileRequest
from rag.nlp.config import MorphologyConfig, NlpConfig
from rag.nlp.normalizer import ZWNJ

PERSIAN_POLICY = (
    "ماده ۵ مرخصی سالانه\n\n"
    "شرایط استفاده از مرخصی سالانه طبق ماده ۵ قانون کار تعیین می‌شود. "
    "کارکنان تمام‌وقت پس از یک سال خدمت مشمول این ماده هستند. "
    "درخواست مرخصی باید حداقل ده روز قبل در سامانه ثبت شود."
)


@pytest.fixture
def nlp_application(identity_store, ingest_permissions) -> RagApplication:
    """Application with the NLP layer and semantic chunking switched on."""
    return RagApplication.build_in_memory(
        identity_store,
        ingest_permissions=ingest_permissions,
        nlp_config=NlpConfig(
            enabled=True, morphology=MorphologyConfig(enabled=True)
        ),
        chunking_config=ChunkingConfig(
            strategy=STRATEGY_SEMANTIC, max_tokens=40, overlap_tokens=8
        ),
        embedding_config=STUB_EMBEDDING_CONFIG,
    )


def _file_request(tenant_ids, data: bytes, **kwargs) -> IngestFileRequest:
    return IngestFileRequest(
        data=data,
        company_id=tenant_ids["companies"]["C1"],
        department_id=tenant_ids["departments"]["C1_D1"],
        source="file-fixture",
        **kwargs,
    )


class TestFileIngestion:
    def test_plain_text_file_ingested(self, rag_application, tenant_ids, request_id):
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, PERSIAN_POLICY.encode(), filename="policy.txt"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count > 0
        document = rag_application.document_store.get(response.document_id)
        assert document.source_type == "text"

    def test_pdf_file_ingested(self, rag_application, tenant_ids, request_id):
        data = build_persian_pdf(["مرخصی سالانه کارکنان", "شرایط ثبت درخواست"])
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, data, filename="policy.pdf"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        document = rag_application.document_store.get(response.document_id)
        assert document.source_type == "pdf"
        assert response.chunk_count > 0

    def test_pdf_page_provenance_recorded_on_chunks(
        self, rag_application, tenant_ids, request_id
    ):
        data = build_pdf(["first page content here", "second page content here"])
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, data, filename="two-pages.pdf"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = rag_application.chunk_store.list_by_document_id(response.document_id)
        assert chunks
        for chunk in chunks:
            assert chunk.source_segment_label == "page"
            assert chunk.source_segment_start is not None
        ordinals = {c.source_segment_start for c in chunks}
        assert ordinals <= {1, 2}

    def test_plain_text_provenance_uses_generic_document_label(
        self, rag_application, tenant_ids, request_id
    ):
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, PERSIAN_POLICY.encode(), filename="a.txt"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = rag_application.chunk_store.list_by_document_id(response.document_id)
        assert all(chunk.source_segment_label == "document" for chunk in chunks)

    def test_pdf_title_metadata_used_when_no_title_given(
        self, rag_application, tenant_ids, request_id
    ):
        data = build_pdf(["body text here"], title="HR Policy Handbook")
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, data, filename="hr.pdf"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        document = rag_application.document_store.get(response.document_id)
        assert document.title == "HR Policy Handbook"

    def test_explicit_title_wins_over_pdf_metadata(
        self, rag_application, tenant_ids, request_id
    ):
        data = build_pdf(["body"], title="Embedded Title")
        response = rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, data, filename="x.pdf", title="Caller Title"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        assert rag_application.document_store.get(response.document_id).title == (
            "Caller Title"
        )

    def test_corrupt_pdf_rejected(self, rag_application, tenant_ids, request_id):
        with pytest.raises(CorruptDocumentError):
            rag_application.ingestion_service.create_document_from_file(
                _file_request(tenant_ids, build_corrupt_pdf(), filename="bad.pdf"),
                request_id,
                tenant_ids["tokens"]["U1"],
            )

    def test_uploaded_pdf_is_retrievable_end_to_end(
        self, rag_application, tenant_ids, request_id, retrieve_handler
    ):
        data = build_persian_pdf(["مرخصی سالانه کارکنان تمام وقت"])
        rag_application.ingestion_service.create_document_from_file(
            _file_request(tenant_ids, data, filename="policy.pdf"),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        response = retrieve_handler.retrieve(
            RetrievalApiRequest(
                query="مرخصی سالانه کارکنان تمام وقت",
                request_id=request_id,
                top_k=5,
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1
        assert "مرخصی" in response.chunks[0].content


class TestNlpEnabledIngestion:
    def test_chunks_record_nlp_version_and_embedding_text(
        self, nlp_application, tenant_ids, request_id
    ):
        response = nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = nlp_application.chunk_store.list_by_document_id(response.document_id)
        assert chunks
        assert all(chunk.nlp_version for chunk in chunks)
        assert all("fa-norm-v2" in chunk.nlp_version for chunk in chunks)
        assert any(chunk.embedding_text for chunk in chunks)

    def test_normalized_content_is_preserved_for_display(
        self, nlp_application, tenant_ids, request_id
    ):
        response = nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = nlp_application.chunk_store.list_by_document_id(response.document_id)
        joined = " ".join(chunk.content for chunk in chunks)
        # Stored content keeps real Persian words, not lemmatized stems.
        assert "مرخصی" in joined
        assert "کارکنان" in joined

    def test_document_records_fa_norm_v2(
        self, nlp_application, tenant_ids, request_id
    ):
        response = nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        document = nlp_application.document_store.get(response.document_id)
        assert document.normalization_version == "fa-norm-v2"

    def test_language_and_offsets_recorded(
        self, nlp_application, tenant_ids, request_id
    ):
        response = nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        for chunk in nlp_application.chunk_store.list_by_document_id(
            response.document_id
        ):
            assert chunk.language == "fa"
            assert chunk.char_start is not None
            assert chunk.char_end >= chunk.char_start
            assert chunk.token_count and chunk.token_count > 0

    def test_semantic_chunking_keeps_heading_with_content(
        self, nlp_application, tenant_ids, request_id
    ):
        response = nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = nlp_application.chunk_store.list_by_document_id(response.document_id)
        heading_chunks = [c for c in chunks if c.content.startswith("ماده ۵")]
        assert heading_chunks
        assert "\n" in heading_chunks[0].content

    def test_default_application_leaves_enrichment_absent(
        self, rag_application, tenant_ids, request_id
    ):
        # NLP is off by default: no version stamp, behaviour unchanged.
        response = rag_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        chunks = rag_application.chunk_store.list_by_document_id(response.document_id)
        assert all(chunk.nlp_version is None for chunk in chunks)
        document = rag_application.document_store.get(response.document_id)
        assert document.normalization_version == "fa-norm-v1"


class TestQuerySideSymmetry:
    def test_query_uses_the_same_nlp_transform_as_documents(self, nlp_application):
        preprocessor = nlp_application.embedding_service.preprocessor
        assert preprocessor.nlp_enabled is True
        assert preprocessor.normalization_version == "fa-norm-v2"

    def test_inflected_query_matches_base_form_document(
        self, nlp_application, tenant_ids, request_id
    ):
        nlp_application.ingestion_service.create_document(
            make_ingest_request(
                tenant_ids, content="راهنمای کتاب سازمانی برای کارکنان جدید"
            ),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        vector_singular = nlp_application.embedding_service.embed_query("کتاب").vector
        vector_plural = nlp_application.embedding_service.embed_query(
            f"کتاب{ZWNJ}ها"
        ).vector
        # Morphology collapses the inflection, so both embed identically.
        assert (vector_singular == vector_plural).all()

    def test_zwnj_and_spaced_spellings_embed_identically(self, nlp_application):
        service = nlp_application.embedding_service
        joined = service.embed_query("میروم").vector
        with_zwnj = service.embed_query(f"می{ZWNJ}روم").vector
        assert (joined == with_zwnj).all()

    def test_arabic_variant_query_embeds_like_persian(self, nlp_application):
        service = nlp_application.embedding_service
        arabic = service.embed_query("مرخصي سالانه").vector
        persian = service.embed_query("مرخصی سالانه").vector
        assert (arabic == persian).all()

    def test_retrieval_still_works_with_nlp_enabled(
        self, nlp_application, tenant_ids, request_id
    ):
        from rag.app.handlers.retrieve import RetrieveHandler

        nlp_application.ingestion_service.create_document(
            make_ingest_request(tenant_ids, content=PERSIAN_POLICY, document_id=uuid4()),
            request_id,
            tenant_ids["tokens"]["U1"],
        )
        handler = RetrieveHandler(nlp_application.retrieval_service)
        response = handler.retrieve(
            RetrievalApiRequest(
                query="مرخصی سالانه", request_id=request_id, top_k=5
            ),
            bearer_token=tenant_ids["tokens"]["U1"],
        )
        assert response.chunk_count >= 1

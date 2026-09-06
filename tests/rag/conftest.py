from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from rag.app.factory import RagApplication
from rag.app.handlers.query import RagQueryHandler
from rag.app.handlers.retrieve import RetrieveHandler
from rag.app.router import RagHttpApplication
from rag.authorization.builder import AuthorizationContextBuilder
from rag.contracts.retrieval import RetrievedChunk
from rag.embedding.config import EmbeddingConfig
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.identity.provider import StoreIdentityProvider
from rag.identity.resolver import IdentityResolutionService, IdentityResolver
from rag.identity.store import (
    CompanyRecord,
    DepartmentRecord,
    EntityStatus,
    InMemoryIdentityStore,
    UserRecord,
    utc_now,
)
from rag.ingestion.audit import IngestAuditLog
from rag.ingestion.authz import IngestAuthorizationService, IngestPermissionRegistry
from rag.ingestion.embedding_integration import embed_and_attach_chunks
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.service import IngestionService
from rag.ingestion.store.document_store import DocumentStore, InMemoryDocumentStore
from rag.ingestion.types import IngestDocumentRequest, StoredChunk
from rag.ingestion.validation import chunk_content_hash
from rag.pipeline.config import PipelineConfig
from rag.pipeline.orchestrator import RagOrchestrator
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.retrieval.engine import SecureRetrievalEngine
from rag.retrieval.service import RetrievalService
from rag.storage.chunk_store import InMemoryChunkStore

FIXTURES_DIR = Path(__file__).parent / "fixtures"

SAMPLE_PERSIAN_CONTENT = (
    "این یک متن نمونه برای تست ingestion است. "
    "سیستم باید متن را نرمال‌سازی، chunk کند و metadata امنیتی را propagate کند. "
) * 8


@pytest.fixture(scope="session")
def tenant_ids() -> dict:
    with (FIXTURES_DIR / "tenants.json").open(encoding="utf-8") as handle:
        raw = json.load(handle)
    return {
        "companies": {k: UUID(v) for k, v in raw["companies"].items()},
        "departments": {k: UUID(v) for k, v in raw["departments"].items()},
        "users": {k: UUID(v) for k, v in raw["users"].items()},
        "tokens": raw["tokens"],
    }


def build_identity_store_for(tenant_ids: dict) -> InMemoryIdentityStore:
    """
    Seed the standard C1/C2 tenant fixture.

    Exposed as a function so tests that need a broader-scoped store (class or
    module) can build one without depending on the function-scoped fixture.
    """
    store = InMemoryIdentityStore()
    c1 = tenant_ids["companies"]["C1"]
    c2 = tenant_ids["companies"]["C2"]
    d1, d2, d3 = (
        tenant_ids["departments"]["C1_D1"],
        tenant_ids["departments"]["C1_D2"],
        tenant_ids["departments"]["C1_D3"],
    )
    c2_d1 = tenant_ids["departments"]["C2_D1"]
    u1, u2, u3, u_disabled, s1 = (
        tenant_ids["users"]["U1"],
        tenant_ids["users"]["U2"],
        tenant_ids["users"]["U3"],
        tenant_ids["users"]["U_DISABLED"],
        tenant_ids["users"]["S1"],
    )

    store.register_company(CompanyRecord(id=c1))
    store.register_company(CompanyRecord(id=c2))
    for department_id, company_id in (
        (d1, c1),
        (d2, c1),
        (d3, c1),
        (c2_d1, c2),
    ):
        store.register_department(DepartmentRecord(id=department_id, company_id=company_id))

    store.register_user(UserRecord(id=u1, company_id=c1), [d1])
    store.register_user(UserRecord(id=u2, company_id=c1), [d1, d3])
    store.register_user(UserRecord(id=u3, company_id=c1), [])
    store.register_user(UserRecord(id=s1, company_id=c1), [])
    store.register_user(
        UserRecord(id=u_disabled, company_id=c1, status=EntityStatus.DISABLED),
        [d1],
    )

    store.register_token(
        UUID("44444444-4444-4444-4444-444444444401"),
        u1,
        tenant_ids["tokens"]["U1"],
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444402"),
        u2,
        tenant_ids["tokens"]["U2"],
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444403"),
        u3,
        tenant_ids["tokens"]["U3"],
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444406"),
        s1,
        tenant_ids["tokens"]["S1"],
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444407"),
        u_disabled,
        tenant_ids["tokens"]["U_DISABLED"],
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444404"),
        u1,
        tenant_ids["tokens"]["REVOKED"],
        revoked_at=utc_now() - timedelta(days=1),
    )
    store.register_token(
        UUID("44444444-4444-4444-4444-444444444405"),
        u1,
        tenant_ids["tokens"]["EXPIRED"],
        expires_at=utc_now() - timedelta(days=1),
    )
    return store


@pytest.fixture
def identity_store(tenant_ids: dict) -> InMemoryIdentityStore:
    return build_identity_store_for(tenant_ids)


@pytest.fixture
def identity_provider(identity_store: InMemoryIdentityStore) -> StoreIdentityProvider:
    return StoreIdentityProvider(identity_store)


@pytest.fixture
def identity_resolver(identity_provider: StoreIdentityProvider) -> IdentityResolver:
    return IdentityResolver(identity_provider)


@pytest.fixture
def identity_service(identity_resolver: IdentityResolver) -> IdentityResolutionService:
    return IdentityResolutionService(
        identity_resolver,
        AuthorizationContextBuilder(),
    )


@pytest.fixture
def request_id() -> UUID:
    return UUID("55555555-5555-5555-5555-555555555501")


@pytest.fixture
def stub_embedding_model() -> StubEmbeddingModel:
    return StubEmbeddingModel(dimension=384, model_id="stub-v1")


@pytest.fixture
def embedding_service(stub_embedding_model: StubEmbeddingModel) -> EmbeddingService:
    return EmbeddingService(stub_embedding_model, EmbeddingPreprocessor())


@pytest.fixture
def document_store() -> DocumentStore:
    return InMemoryDocumentStore()


@pytest.fixture
def chunk_store() -> InMemoryChunkStore:
    return InMemoryChunkStore()


@pytest.fixture
def audit_log() -> IngestAuditLog:
    return IngestAuditLog()


@pytest.fixture
def ingest_permissions(tenant_ids: dict) -> IngestPermissionRegistry:
    registry = IngestPermissionRegistry()
    registry.grant_company_wide(tenant_ids["users"]["S1"])
    return registry


#: Tests pin their own embedding model instead of inheriting the production
#: config. Without this, every application-level test would load the real
#: production model (a ~2 GB download and tens of seconds per fixture).
STUB_EMBEDDING_CONFIG = EmbeddingConfig(
    backend="stub",
    model_id="stub-v1",
    device="cpu",
    batch_size=32,
    normalize_embeddings=True,
)


@pytest.fixture
def rag_application(
    identity_store: InMemoryIdentityStore,
    ingest_permissions: IngestPermissionRegistry,
) -> RagApplication:
    return RagApplication.build_in_memory(
        identity_store,
        ingest_permissions=ingest_permissions,
        embedding_config=STUB_EMBEDDING_CONFIG,
    )


@pytest.fixture
def retrieve_handler(rag_application: RagApplication) -> RetrieveHandler:
    # Wired with the application's limiter so the enforced path is the tested path.
    return RetrieveHandler(
        rag_application.retrieval_service,
        rag_application.rate_limiter,
        rag_application.request_limits,
    )


@pytest.fixture
def rag_query_handler(rag_application: RagApplication) -> RagQueryHandler:
    return RagQueryHandler(
        rag_application.rag_orchestrator,
        rag_application.rate_limiter,
        rag_application.request_limits,
    )


@pytest.fixture
def rag_http_app(
    retrieve_handler: RetrieveHandler,
    rag_query_handler: RagQueryHandler,
    rag_application: RagApplication,
) -> RagHttpApplication:
    return RagHttpApplication(
        retrieve_handler,
        rag_query_handler,
        health_service=rag_application.health_service,
    )


@pytest.fixture
def ingest_authz(
    identity_provider: StoreIdentityProvider,
    ingest_permissions: IngestPermissionRegistry,
) -> IngestAuthorizationService:
    return IngestAuthorizationService(identity_provider, ingest_permissions)


@pytest.fixture
def ingestion_pipeline(
    document_store: DocumentStore,
    chunk_store: InMemoryChunkStore,
    embedding_service: EmbeddingService,
    audit_log: IngestAuditLog,
) -> IngestionPipeline:
    return IngestionPipeline(document_store, chunk_store, embedding_service, audit_log)


@pytest.fixture
def ingestion_service(
    identity_service: IdentityResolutionService,
    ingest_authz: IngestAuthorizationService,
    ingestion_pipeline: IngestionPipeline,
    document_store: DocumentStore,
    chunk_store: InMemoryChunkStore,
) -> IngestionService:
    return IngestionService(
        identity_service,
        ingest_authz,
        ingestion_pipeline,
        document_store,
        chunk_store,
    )


@pytest.fixture
def retrieval_engine(
    embedding_service: EmbeddingService,
    chunk_store: InMemoryChunkStore,
    document_store: DocumentStore,
) -> SecureRetrievalEngine:
    return SecureRetrievalEngine(embedding_service, chunk_store, document_store)


@pytest.fixture
def retrieval_service(
    identity_service: IdentityResolutionService,
    retrieval_engine: SecureRetrievalEngine,
) -> RetrievalService:
    return RetrievalService(identity_service, retrieval_engine)


@pytest.fixture
def pipeline_config() -> PipelineConfig:
    return PipelineConfig()


@pytest.fixture
def post_retrieval_pipeline(pipeline_config: PipelineConfig) -> PostRetrievalPipeline:
    return PostRetrievalPipeline(pipeline_config)


@pytest.fixture
def rag_orchestrator(
    retrieval_service: RetrievalService,
    post_retrieval_pipeline: PostRetrievalPipeline,
    document_store: DocumentStore,
) -> RagOrchestrator:
    return RagOrchestrator(
        retrieval_service,
        post_retrieval_pipeline,
        document_store=document_store,
    )


def make_retrieved_chunk(
    content: str,
    *,
    score: float,
    company_id: UUID,
    department_id: UUID,
    chunk_id: UUID | None = None,
    document_id: UUID | None = None,
    chunk_index: int = 0,
    document_version: int = 1,
) -> RetrievedChunk:
    """Build an authorized retrieval candidate for post-retrieval pipeline tests."""
    return RetrievedChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=document_id or uuid4(),
        company_id=company_id,
        department_id=department_id,
        content=content,
        score=score,
        chunk_index=chunk_index,
        document_version=document_version,
    )


def make_ingest_request(
    tenant_ids: dict,
    *,
    company_key: str = "C1",
    department_key: str = "C1_D1",
    content: str = SAMPLE_PERSIAN_CONTENT,
    **kwargs: object,
) -> IngestDocumentRequest:
    return IngestDocumentRequest(
        content=content,
        company_id=tenant_ids["companies"][company_key],
        department_id=tenant_ids["departments"][department_key],
        source="test-fixture",
        **kwargs,
    )


def make_embedded_stored_chunk(
    embedding_service: EmbeddingService,
    *,
    chunk_id,
    document_id,
    company_id,
    department_id,
    content: str,
    document_version: int = 1,
    chunk_index: int = 0,
    document_status: str = "indexed",
) -> StoredChunk:
    """
    Build a StoredChunk with a valid stub embedding for direct store seeding.

    Defaults to `document_status="indexed"` because tests that seed the store
    directly are standing in for already-ingested content. Chunks written by
    `IngestionPipeline` start PROCESSING and are published on commit.
    """
    draft = StoredChunk(
        chunk_id=chunk_id,
        document_id=document_id,
        company_id=company_id,
        department_id=department_id,
        document_version=document_version,
        chunk_index=chunk_index,
        content=content,
        content_hash=chunk_content_hash(content),
        document_status=document_status,
    )
    return embed_and_attach_chunks(embedding_service, [draft])[0]

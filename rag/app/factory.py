"""Application dependency wiring — single shared embedding service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rag.app.health import HealthService, build_health_service
from rag.app.limits import (
    RequestLimits,
    load_extraction_limits,
    load_request_limits,
)
from rag.app.rate_limit import (
    ConcurrencyLimiter,
    RateLimitConfig,
    RateLimiter,
    load_rate_limit_config,
)
from rag.audit import AuditLog
from rag.authorization.builder import AuthorizationContextBuilder
from rag.embedding.config import EmbeddingConfig, load_embedding_config
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.identity.provider import StoreIdentityProvider
from rag.identity.resolver import IdentityResolutionService, IdentityResolver
from rag.identity.store import InMemoryIdentityStore
from rag.ingestion.authz import IngestAuthorizationService, IngestPermissionRegistry
from rag.ingestion.chunking import ChunkingConfig, create_chunker, load_chunking_config
from rag.ingestion.extraction.registry import ExtractorRegistry
from rag.ingestion.pipeline import IngestionPipeline
from rag.ingestion.service import IngestionService
from rag.ingestion.store.document_store import DocumentStore, InMemoryDocumentStore
from rag.nlp.config import NlpConfig, load_nlp_config
from rag.nlp.pipeline import PersianNlpPipeline
from rag.pipeline.config import PipelineConfig, load_pipeline_config
from rag.pipeline.orchestrator import RagOrchestrator
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.retrieval.config import RetrievalConfig, load_retrieval_config
from rag.retrieval.engine import SecureRetrievalEngine
from rag.retrieval.metrics import RetrievalMetrics
from rag.retrieval.service import RetrievalService
from rag.storage.chunk_store import ChunkStore, InMemoryChunkStore
from rag.storage.config import VectorStoreConfig, load_vector_store_config
from rag.storage.factory import create_chunk_store


def create_embedding_service(
    config: EmbeddingConfig | None = None,
    *,
    nlp: PersianNlpPipeline | None = None,
    concurrency_limiter: object | None = None,
) -> EmbeddingService:
    embedding_config = config or load_embedding_config()
    model = ModelRegistry.create(embedding_config)
    version = (
        nlp.config.normalization_version
        if nlp is not None and nlp.config.enabled
        else embedding_config.preprocessing.normalization_version
    )
    return EmbeddingService(
        model,
        EmbeddingPreprocessor(version, nlp=nlp),
        concurrency_limiter=concurrency_limiter,
    )


@dataclass(slots=True)
class RagApplication:
    """Shared in-process application context for ingestion and retrieval."""

    identity_store: InMemoryIdentityStore
    identity_service: IdentityResolutionService
    embedding_service: EmbeddingService
    document_store: DocumentStore
    chunk_store: ChunkStore
    ingestion_service: IngestionService
    retrieval_service: RetrievalService
    retrieval_metrics: RetrievalMetrics
    post_retrieval_pipeline: PostRetrievalPipeline
    rag_orchestrator: RagOrchestrator
    pipeline_config: PipelineConfig
    nlp_pipeline: PersianNlpPipeline
    chunking_config: ChunkingConfig
    audit_log: AuditLog
    health_service: HealthService
    rate_limiter: RateLimiter
    request_limits: RequestLimits

    @classmethod
    def build_in_memory(
        cls,
        identity_store: InMemoryIdentityStore,
        *,
        ingest_permissions: IngestPermissionRegistry | None = None,
        embedding_config: EmbeddingConfig | None = None,
        embedding_config_path: Path | None = None,
        retrieval_config: RetrievalConfig | None = None,
        retrieval_config_path: Path | None = None,
        pipeline_config: PipelineConfig | None = None,
        pipeline_config_path: Path | None = None,
        nlp_config: NlpConfig | None = None,
        nlp_config_path: Path | None = None,
        chunking_config: ChunkingConfig | None = None,
        chunking_config_path: Path | None = None,
        chunk_store: ChunkStore | None = None,
        document_store: DocumentStore | None = None,
        vector_store_config: VectorStoreConfig | None = None,
        vector_store_config_path: Path | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        rate_limit_config_path: Path | None = None,
        request_limits: RequestLimits | None = None,
        request_limits_path: Path | None = None,
    ) -> RagApplication:
        limits = request_limits
        if limits is None and request_limits_path is not None:
            limits = load_request_limits(request_limits_path)
        limits = limits or load_request_limits()
        extraction_limits = load_extraction_limits(request_limits_path)

        rate_limit_cfg = rate_limit_config
        if rate_limit_cfg is None and rate_limit_config_path is not None:
            rate_limit_cfg = load_rate_limit_config(rate_limit_config_path)
        rate_limit_cfg = rate_limit_cfg or load_rate_limit_config()
        rate_limiter = RateLimiter(rate_limit_cfg)
        embedding_concurrency = (
            ConcurrencyLimiter(
                rate_limit_cfg.max_concurrent_embeddings,
                rate_limit_cfg.embedding_wait_seconds,
            )
            if rate_limit_cfg.enabled
            else None
        )

        nlp_cfg = nlp_config
        if nlp_cfg is None and nlp_config_path is not None:
            nlp_cfg = load_nlp_config(nlp_config_path)
        nlp_cfg = nlp_cfg or load_nlp_config()
        nlp_pipeline = PersianNlpPipeline(nlp_cfg)

        chunking_cfg = chunking_config
        if chunking_cfg is None and chunking_config_path is not None:
            chunking_cfg = load_chunking_config(chunking_config_path)
        chunking_cfg = chunking_cfg or load_chunking_config()

        config = embedding_config
        if config is None and embedding_config_path is not None:
            config = load_embedding_config(embedding_config_path)
        embedding_service = create_embedding_service(
            config, nlp=nlp_pipeline, concurrency_limiter=embedding_concurrency
        )

        retrieval_cfg = retrieval_config
        if retrieval_cfg is None and retrieval_config_path is not None:
            retrieval_cfg = load_retrieval_config(retrieval_config_path)
        retrieval_cfg = retrieval_cfg or load_retrieval_config()

        pipeline_cfg = pipeline_config
        if pipeline_cfg is None and pipeline_config_path is not None:
            pipeline_cfg = load_pipeline_config(pipeline_config_path)
        pipeline_cfg = pipeline_cfg or load_pipeline_config()

        # A durable store can be injected; otherwise state is process-local.
        document_store = (
            document_store if document_store is not None else InMemoryDocumentStore()
        )
        # Any ChunkStore implementation is accepted. An explicit instance wins;
        # otherwise the configured backend decides (memory by default), so
        # switching to Weaviate is a configuration change, not a code change.
        if chunk_store is None:
            vector_cfg = vector_store_config
            if vector_cfg is None and vector_store_config_path is not None:
                vector_cfg = load_vector_store_config(vector_store_config_path)
            chunk_store = (
                create_chunk_store(vector_cfg)
                if vector_cfg is not None
                else InMemoryChunkStore()
            )
        # One audit trail across ingestion and retrieval.
        audit_log = AuditLog()
        retrieval_metrics = RetrievalMetrics()

        identity_provider = StoreIdentityProvider(identity_store)
        identity_resolver = IdentityResolver(identity_provider)
        identity_service = IdentityResolutionService(
            identity_resolver,
            AuthorizationContextBuilder(),
        )

        permissions = ingest_permissions or IngestPermissionRegistry()
        ingest_authz = IngestAuthorizationService(identity_provider, permissions)

        pipeline = IngestionPipeline(
            document_store,
            chunk_store,
            embedding_service,
            audit_log,
            chunker=create_chunker(chunking_cfg),
            nlp=nlp_pipeline,
        )
        ingestion_service = IngestionService(
            identity_service,
            ingest_authz,
            pipeline,
            document_store,
            chunk_store,
            extractors=ExtractorRegistry(limits=extraction_limits),
            rate_limiter=rate_limiter,
        )

        retrieval_engine = SecureRetrievalEngine(
            embedding_service,
            chunk_store,
            document_store,
            retrieval_metrics,
            config=retrieval_cfg,
            audit_log=audit_log,
        )
        retrieval_service = RetrievalService(identity_service, retrieval_engine)

        post_retrieval_pipeline = PostRetrievalPipeline(pipeline_cfg)
        rag_orchestrator = RagOrchestrator(
            retrieval_service,
            post_retrieval_pipeline,
            config=pipeline_cfg,
            document_store=document_store,
        )

        health_service = build_health_service(
            embedding_service=embedding_service,
            chunk_store=chunk_store,
            document_store=document_store,
            identity_store=identity_store,
        )

        return cls(
            identity_store=identity_store,
            identity_service=identity_service,
            embedding_service=embedding_service,
            document_store=document_store,
            chunk_store=chunk_store,
            ingestion_service=ingestion_service,
            retrieval_service=retrieval_service,
            retrieval_metrics=retrieval_metrics,
            post_retrieval_pipeline=post_retrieval_pipeline,
            rag_orchestrator=rag_orchestrator,
            pipeline_config=pipeline_cfg,
            nlp_pipeline=nlp_pipeline,
            chunking_config=chunking_cfg,
            audit_log=audit_log,
            health_service=health_service,
            rate_limiter=rate_limiter,
            request_limits=limits,
        )

"""
Security regression: reranking cannot expand retrieval scope.

SEC-RR-002 / PP-SEC-001..004, reranker.md RR-001..RR-006.
"""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import UUID

import pytest

from rag.authorization.context import AuthorizationContext
from rag.pipeline.errors import RerankContractViolationError
from rag.pipeline.pipeline import PostRetrievalPipeline
from rag.pipeline.reranker import LexicalReranker, NoOpReranker, validate_rerank_contract
from rag.pipeline.types import (
    AppliedFilter,
    PipelineOptions,
    RerankResult,
    RetrievalMetadata,
)
from rag.storage.chunk_store import InMemoryChunkStore
from tests.rag.conftest import make_retrieved_chunk

PIPELINE_DIR = Path(__file__).resolve().parents[3] / "rag" / "pipeline"

# The orchestrator is the composition root and is *expected* to hold the
# retrieval boundary; every other pipeline module must be store-free.
STORE_FREE_MODULES = (
    "reranker.py",
    "pipeline.py",
    "selector.py",
    "deduplicator.py",
    "context_builder.py",
    "provenance.py",
    "validation.py",
    "tokenizer.py",
    "ordering.py",
    "serialization.py",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "rag.storage",
    "rag.embedding",
    "rag.ingestion.store",
    "rag.retrieval.engine",
    "rag.retrieval.service",
    "rag.retrieval.candidates",
)

COMPANY_A = UUID("11111111-1111-1111-1111-111111111101")
COMPANY_B = UUID("11111111-1111-1111-1111-111111111102")
DEPARTMENT_A = UUID("22222222-2222-2222-2222-222222222201")
DEPARTMENT_B = UUID("22222222-2222-2222-2222-222222222202")
USER = UUID("33333333-3333-3333-3333-333333333301")
REQUEST = UUID("55555555-5555-5555-5555-555555555501")


def _authorized(content: str, score: float, **kwargs):
    return make_retrieved_chunk(
        content,
        score=score,
        company_id=COMPANY_A,
        department_id=DEPARTMENT_A,
        **kwargs,
    )


def _foreign(content: str, score: float):
    return make_retrieved_chunk(
        content,
        score=score,
        company_id=COMPANY_B,
        department_id=DEPARTMENT_B,
    )


def _module_imports(filename: str) -> set[str]:
    tree = ast.parse((PIPELINE_DIR / filename).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


class SmugglingReranker:
    """Hostile reranker that tries to inject a chunk it was never given."""

    def __init__(self, smuggled):
        self._smuggled = smuggled

    @property
    def model_id(self) -> str | None:
        return "smuggling-reranker"

    def rerank(self, query, candidates):
        return RerankResult(
            candidates=(*candidates, self._smuggled),
            rerank_scores={self._smuggled.chunk_id: 1.0},
            latency_ms=0,
            model_id=self.model_id,
        )


class DroppingReranker:
    """Hostile reranker that silently drops chunks."""

    @property
    def model_id(self) -> str | None:
        return "dropping-reranker"

    def rerank(self, query, candidates):
        return RerankResult(
            candidates=tuple(candidates)[:1],
            rerank_scores={},
            latency_ms=0,
            model_id=self.model_id,
        )


@pytest.fixture
def authorization_context() -> AuthorizationContext:
    return AuthorizationContext(
        user_id=USER,
        company_id=COMPANY_A,
        allowed_department_ids=(DEPARTMENT_A,),
        request_id=REQUEST,
    )


def _retrieval_metadata(count: int) -> RetrievalMetadata:
    return RetrievalMetadata(
        chunk_count=count,
        latency_ms=5,
        filter_applied=AppliedFilter(company_id=COMPANY_A, department_count=1),
    )


@pytest.mark.security
class TestRerankerHasNoStoreAccess:
    def test_pp_sec_002_pipeline_modules_do_not_import_stores(self):
        for filename in STORE_FREE_MODULES:
            for imported in _module_imports(filename):
                assert not imported.startswith(FORBIDDEN_IMPORT_PREFIXES), (
                    f"{filename} imports {imported}, which would give the "
                    "post-retrieval pipeline corpus access"
                )

    def test_pp_sec_002_reranker_di_graph_has_no_store(self):
        for reranker in (NoOpReranker(), LexicalReranker()):
            for value in vars(reranker).values():
                assert not isinstance(value, InMemoryChunkStore)
                assert not hasattr(value, "search")

    def test_pp_sec_002_pipeline_holds_no_store_reference(self):
        pipeline = PostRetrievalPipeline()
        for value in vars(pipeline).values():
            assert not isinstance(value, InMemoryChunkStore)

    def test_reranker_signature_takes_no_authorization_context(self):
        # RR-004: no parameter through which scope could be widened.
        import inspect

        for reranker in (NoOpReranker(), LexicalReranker()):
            parameters = inspect.signature(reranker.rerank).parameters
            assert set(parameters) == {"query", "candidates"}


@pytest.mark.security
class TestRerankPreservesCandidateSet:
    def test_pp_sec_001_chunk_ids_identical_in_and_out(self):
        candidates = [_authorized(f"body {index}", 0.9 - index * 0.05) for index in range(8)]
        for reranker in (NoOpReranker(), LexicalReranker()):
            result = reranker.rerank("body", candidates)
            assert {c.chunk_id for c in result.candidates} == {
                c.chunk_id for c in candidates
            }

    def test_pp_sec_004_fifty_candidates_count_unchanged(self):
        candidates = [_authorized(f"body {index}", 0.9) for index in range(50)]
        result = LexicalReranker().rerank("body", candidates)
        assert len(result.candidates) == 50
        validate_rerank_contract(candidates, result)

    def test_pp_sec_003_smuggled_chunk_is_rejected(self, authorization_context):
        smuggled = _foreign("other company secret", 0.99)
        pipeline = PostRetrievalPipeline(reranker=SmugglingReranker(smuggled))
        candidates = [_authorized("authorized body", 0.5)]
        with pytest.raises(RerankContractViolationError) as exc_info:
            pipeline.process(
                "query",
                authorization_context,
                candidates,
                _retrieval_metadata(1),
                PipelineOptions(rerank=True, top_k=5),
            )
        # Fails closed without naming or echoing the smuggled content.
        assert "other company secret" not in str(exc_info.value)

    def test_dropping_reranker_is_rejected(self, authorization_context):
        pipeline = PostRetrievalPipeline(reranker=DroppingReranker())
        candidates = [_authorized(f"body {index}", 0.5) for index in range(3)]
        with pytest.raises(RerankContractViolationError):
            pipeline.process(
                "query",
                authorization_context,
                candidates,
                _retrieval_metadata(3),
                PipelineOptions(rerank=True, top_k=5),
            )

    def test_rerank_disabled_leaves_candidates_untouched(self, authorization_context):
        pipeline = PostRetrievalPipeline(reranker=SmugglingReranker(_foreign("x", 1.0)))
        candidates = [_authorized(f"body {index}", 0.9 - index * 0.1) for index in range(3)]
        result = pipeline.process(
            "query",
            authorization_context,
            candidates,
            _retrieval_metadata(3),
            PipelineOptions(rerank=False, top_k=5),
        )
        # RR-006: with rerank disabled the reranker is never invoked at all.
        assert len(result.chunks) == 3
        assert result.pipeline.rerank_enabled is False
        assert result.pipeline.rerank_model_id is None

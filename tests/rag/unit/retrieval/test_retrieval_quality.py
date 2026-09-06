"""Unit tests for Phase 4 retrieval quality pipeline."""

from __future__ import annotations

from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from rag.ingestion.persian import normalize_persian
from rag.ingestion.types import StoredChunk
from rag.retrieval.config import RetrievalConfig
from rag.retrieval.context import ContextAssembler
from rag.retrieval.deduplicator import Deduplicator
from rag.retrieval.diversity import DiversityFilter
from rag.retrieval.errors import RetrievalValidationError
from rag.retrieval.lexical import phrase_match_score, token_overlap_score
from rag.retrieval.pipeline import RetrievalQualityPipeline
from rag.retrieval.reranker import Ranker
from rag.retrieval.types import RankedCandidate, SemanticCandidate


def _chunk(
    content: str,
    *,
    chunk_id: UUID | None = None,
    document_id: UUID | None = None,
    chunk_index: int = 0,
) -> StoredChunk:
    return StoredChunk(
        chunk_id=chunk_id or uuid4(),
        document_id=document_id or uuid4(),
        company_id=UUID("11111111-1111-1111-1111-111111111101"),
        department_id=UUID("22222222-2222-2222-2222-222222222201"),
        document_version=1,
        chunk_index=chunk_index,
        content=content,
        content_hash="test-hash",
    )


def _semantic(
    content: str,
    semantic_score: float,
    *,
    rank_before: int = 1,
    document_id: UUID | None = None,
) -> SemanticCandidate:
    return SemanticCandidate(
        chunk=_chunk(content, document_id=document_id),
        semantic_score=semantic_score,
        rank_before=rank_before,
    )


class TestLexicalScoring:
    def test_exact_phrase_match(self):
        query = "مرخصی سالانه"
        content = "کارکنان حق مرخصی سالانه دارند."
        assert phrase_match_score(query, content) == 1.0

    def test_token_overlap_hand_calculated(self):
        query = "مرخصی سالانه"
        content = "سالانه و مرخصی"
        # Both tokens appear after normalization.
        assert token_overlap_score(query, content) == 1.0

        partial = "فقط مرخصی"
        assert token_overlap_score(query, partial) == 0.5

    def test_no_overlap_is_zero(self):
        assert token_overlap_score("مرخصی سالانه", "راهنمای فنی سرور") == 0.0

    def test_empty_query_tokens_yield_zero(self):
        assert token_overlap_score("   ", "some content") == 0.0
        assert phrase_match_score("   ", "some content") == 0.0

    def test_zwnj_equivalence(self):
        zwnj = "\u200c"
        with_zwnj = f"مرخصی{zwnj}سالانه"
        without_zwnj = "مرخصی سالانه"
        content = f"حق {without_zwnj} برای کارکنان"
        assert phrase_match_score(with_zwnj, content) == phrase_match_score(
            without_zwnj, content
        )

    def test_arabic_persian_character_variants(self):
        arabic = "مرخصي سالانه"  # Arabic yeh
        persian = "مرخصی سالانه"
        content = "سیاست " + persian
        assert phrase_match_score(arabic, content) == 1.0
        assert token_overlap_score(arabic, content) == token_overlap_score(
            persian, content
        )

    def test_determinism(self):
        query = "مرخصی سالانه"
        content = "مرخصی سالانه ۲۶ روز"
        first = (token_overlap_score(query, content), phrase_match_score(query, content))
        second = (token_overlap_score(query, content), phrase_match_score(query, content))
        assert first == second


class TestReranker:
    def test_lexical_evidence_reorders_semantic_leader(self):
        config = RetrievalConfig(
            semantic_weight=0.7,
            lexical_weight=0.2,
            phrase_weight=0.1,
        )
        ranker = Ranker(config)
        query = "مرخصی سالانه"
        high_semantic = _semantic("راهنمای فنی unrelated topic", 0.95, rank_before=1)
        lexical_winner = _semantic(
            "کارکنان حق مرخصی سالانه دارند.",
            0.80,
            rank_before=2,
        )
        ranked = ranker.rerank(query, [high_semantic, lexical_winner])
        assert ranked[0].chunk.content == lexical_winner.chunk.content
        assert ranked[0].rank_after == 1
        assert ranked[0].final_score > ranked[1].final_score

    def test_strong_semantic_not_destroyed_by_weak_lexical(self):
        config = RetrievalConfig()
        ranker = Ranker(config)
        query = "مرخصی سالانه"
        strong = _semantic("topic alpha", 0.99, rank_before=1)
        weak = _semantic("مرخصی", 0.50, rank_before=2)
        ranked = ranker.rerank(query, [strong, weak])
        assert ranked[0].chunk.content == strong.chunk.content

    def test_final_score_formula(self):
        config = RetrievalConfig(
            semantic_weight=0.7,
            lexical_weight=0.2,
            phrase_weight=0.1,
        )
        ranker = Ranker(config)
        query = "مرخصی سالانه"
        candidate = _semantic("مرخصی سالانه برای کارکنان", 0.8, rank_before=1)
        ranked = ranker.rerank(query, [candidate])[0]
        expected = 0.7 * 0.8 + 0.2 * 1.0 + 0.1 * 1.0
        assert ranked.final_score == pytest.approx(expected)
        assert ranked.lexical_score == 1.0
        assert ranked.phrase_match == 1.0
        assert ranked.semantic_score == 0.8


class TestDeduplication:
    def test_duplicate_chunk_id_collapses(self):
        chunk_id = uuid4()
        doc_id = uuid4()
        content = "duplicate body"
        first = RankedCandidate(
            chunk=_chunk(content, chunk_id=chunk_id, document_id=doc_id),
            semantic_score=0.9,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.8,
            rank_before=1,
            rank_after=1,
        )
        second = RankedCandidate(
            chunk=_chunk(content, chunk_id=chunk_id, document_id=doc_id),
            semantic_score=0.85,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.75,
            rank_before=2,
            rank_after=2,
        )
        result = Deduplicator().deduplicate([first, second])
        assert len(result) == 1

    def test_duplicate_normalized_content_collapses(self):
        zwnj = "\u200c"
        first = RankedCandidate(
            chunk=_chunk(f"مرخصی{zwnj}سالانه"),
            semantic_score=0.9,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.8,
            rank_before=1,
            rank_after=1,
        )
        second = RankedCandidate(
            chunk=_chunk("مرخصی سالانه"),
            semantic_score=0.85,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.75,
            rank_before=2,
            rank_after=2,
        )
        result = Deduplicator().deduplicate([first, second])
        assert len(result) == 1

    def test_same_document_different_content_kept(self):
        doc_id = uuid4()
        first = RankedCandidate(
            chunk=_chunk("chunk one", document_id=doc_id, chunk_index=0),
            semantic_score=0.9,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.8,
            rank_before=1,
            rank_after=1,
        )
        second = RankedCandidate(
            chunk=_chunk("chunk two", document_id=doc_id, chunk_index=1),
            semantic_score=0.85,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.75,
            rank_before=2,
            rank_after=2,
        )
        result = Deduplicator().deduplicate([first, second])
        assert len(result) == 2

    def test_different_documents_same_content_keeps_first(self):
        first = RankedCandidate(
            chunk=_chunk("shared text", document_id=uuid4()),
            semantic_score=0.9,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.8,
            rank_before=1,
            rank_after=1,
        )
        second = RankedCandidate(
            chunk=_chunk("shared text", document_id=uuid4()),
            semantic_score=0.85,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.75,
            rank_before=2,
            rank_after=2,
        )
        result = Deduplicator().deduplicate([first, second])
        assert len(result) == 1
        assert result[0].chunk.document_id == first.chunk.document_id


class TestDiversity:
    def test_no_limit_preserves_all(self):
        doc_id = uuid4()
        ranked = [
            RankedCandidate(
                chunk=_chunk(f"chunk {index}", document_id=doc_id, chunk_index=index),
                semantic_score=0.9 - index * 0.01,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9 - index * 0.01,
                rank_before=index + 1,
                rank_after=index + 1,
            )
            for index in range(3)
        ]
        result = DiversityFilter().apply(ranked, max_chunks_per_document=None)
        assert len(result) == 3

    def test_max_chunks_per_document_enforced(self):
        doc_id = uuid4()
        ranked = [
            RankedCandidate(
                chunk=_chunk(f"chunk {index}", document_id=doc_id, chunk_index=index),
                semantic_score=0.9 - index * 0.01,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9 - index * 0.01,
                rank_before=index + 1,
                rank_after=index + 1,
            )
            for index in range(3)
        ]
        result = DiversityFilter().apply(ranked, max_chunks_per_document=1)
        assert len(result) == 1


class TestContextAssembly:
    def test_empty_results(self):
        context = ContextAssembler().assemble([], max_context_chars=1000)
        assert context.text == ""
        assert context.char_count == 0
        assert context.truncated is False
        assert context.included_chunk_ids == ()

    def test_one_result(self):
        candidate = RankedCandidate(
            chunk=_chunk("body one", document_id=uuid4()),
            semantic_score=0.9,
            lexical_score=0.5,
            phrase_match=0.0,
            final_score=0.8,
            rank_before=1,
            rank_after=1,
        )
        context = ContextAssembler().assemble([candidate], max_context_chars=1000)
        assert "[Document:" in context.text
        assert "body one" in context.text
        assert context.truncated is False
        assert len(context.included_chunk_ids) == 1

    def test_ordering_preserved(self):
        doc_a, doc_b = uuid4(), uuid4()
        ranked = [
            RankedCandidate(
                chunk=_chunk("first", document_id=doc_a),
                semantic_score=0.9,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9,
                rank_before=1,
                rank_after=1,
            ),
            RankedCandidate(
                chunk=_chunk("second", document_id=doc_b),
                semantic_score=0.8,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.8,
                rank_before=2,
                rank_after=2,
            ),
        ]
        context = ContextAssembler().assemble(ranked, max_context_chars=1000)
        assert context.text.index("first") < context.text.index("second")

    def test_context_char_limit(self):
        ranked = [
            RankedCandidate(
                chunk=_chunk("x" * 200, document_id=uuid4()),
                semantic_score=0.9,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9,
                rank_before=1,
                rank_after=1,
            ),
            RankedCandidate(
                chunk=_chunk("y" * 200, document_id=uuid4()),
                semantic_score=0.8,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.8,
                rank_before=2,
                rank_after=2,
            ),
        ]
        context = ContextAssembler().assemble(ranked, max_context_chars=250)
        assert context.char_count <= 250
        assert context.truncated is True
        assert len(context.included_chunk_ids) == 1

    def test_chunk_boundary_preserved(self):
        content = "complete chunk body"
        ranked = [
            RankedCandidate(
                chunk=_chunk(content, document_id=uuid4()),
                semantic_score=0.9,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9,
                rank_before=1,
                rank_after=1,
            ),
        ]
        context = ContextAssembler().assemble(ranked, max_context_chars=10_000)
        assert content in context.text
        assert content[:-1] not in context.text or content in context.text

    def test_deterministic_output(self):
        ranked = [
            RankedCandidate(
                chunk=_chunk("alpha", document_id=uuid4()),
                semantic_score=0.9,
                lexical_score=0.0,
                phrase_match=0.0,
                final_score=0.9,
                rank_before=1,
                rank_after=1,
            ),
        ]
        assembler = ContextAssembler()
        first = assembler.assemble(ranked, max_context_chars=500)
        second = assembler.assemble(ranked, max_context_chars=500)
        assert first == second


class TestRetrievalConfig:
    def test_validate_k_rejects_invalid_values(self):
        config = RetrievalConfig()
        with pytest.raises(RetrievalValidationError):
            config.validate_k(candidate_k=5, final_k=10)
        with pytest.raises(RetrievalValidationError):
            config.validate_k(candidate_k=10, final_k=0)


class TestPipeline:
    def test_diagnostics_when_requested(self):
        pipeline = RetrievalQualityPipeline(RetrievalConfig())
        query = "مرخصی سالانه"
        candidates = [
            _semantic("مرخصی سالانه برای کارکنان", 0.9, rank_before=1),
        ]
        result = pipeline.process(query, candidates, final_k=1, include_diagnostics=True)
        assert result.diagnostics is not None
        assert len(result.diagnostics) == 1
        diag = result.diagnostics[0]
        assert diag.semantic_score == 0.9
        assert diag.final_score > 0

    def test_normalized_content_key_uses_existing_normalizer(self):
        pipeline = RetrievalQualityPipeline(RetrievalConfig())
        query = "test"
        zwnj = "\u200c"
        zwnj_chunk = _semantic(f"مرخصی{zwnj}سالانه", 0.9, rank_before=1)
        plain = _semantic("مرخصی سالانه", 0.85, rank_before=2)
        result = pipeline.process(query, [zwnj_chunk, plain], final_k=5)
        assert len(result.chunks) == 1
        assert normalize_persian(result.chunks[0].chunk.content) == normalize_persian(
            "مرخصی سالانه"
        )


class TestPipelineSecurityHooks:
    def test_ranker_not_called_without_authorization_path(
        self,
        retrieval_engine,
        tenant_ids,
        request_id,
    ):
        from rag.authorization.context import AuthorizationContext

        authz = AuthorizationContext(
            user_id=tenant_ids["users"]["U3"],
            company_id=tenant_ids["companies"]["C1"],
            allowed_department_ids=(),
            request_id=request_id,
        )
        with patch.object(Ranker, "rerank") as rerank_spy:
            result = retrieval_engine.search("query", authz)
            rerank_spy.assert_not_called()
        assert result.chunks == ()

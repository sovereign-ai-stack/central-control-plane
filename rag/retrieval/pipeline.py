"""Post-authorization retrieval quality pipeline."""

from __future__ import annotations

from rag.retrieval.config import RetrievalConfig
from rag.retrieval.context import ContextAssembler
from rag.retrieval.deduplicator import Deduplicator
from rag.retrieval.diversity import DiversityFilter
from rag.retrieval.reranker import Ranker
from rag.retrieval.types import ChunkDiagnostic, PipelineResult, RankedCandidate


class RetrievalQualityPipeline:
    """Rerank, deduplicate, diversify, and assemble context over authorized candidates."""

    def __init__(self, config: RetrievalConfig | None = None) -> None:
        self._config = config or RetrievalConfig()
        self._deduplicator = Deduplicator()
        self._diversity = DiversityFilter()
        self._context = ContextAssembler()
        self._ranker = Ranker(self._config)

    @property
    def config(self) -> RetrievalConfig:
        return self._config

    def process(
        self,
        query: str,
        candidates: list,
        *,
        final_k: int,
        include_diagnostics: bool = False,
    ) -> PipelineResult:
        ranked = self._ranker.rerank(query, candidates)
        ranked = self._deduplicator.deduplicate(ranked)
        ranked = self._diversity.apply(
            ranked,
            max_chunks_per_document=self._config.max_chunks_per_document,
        )
        final = ranked[:final_k]
        context = self._context.assemble(
            final,
            max_context_chars=self._config.max_context_chars,
        )
        diagnostics = (
            tuple(self._to_diagnostic(item) for item in final)
            if include_diagnostics
            else None
        )
        return PipelineResult(chunks=tuple(final), context=context, diagnostics=diagnostics)

    @staticmethod
    def _to_diagnostic(candidate: RankedCandidate) -> ChunkDiagnostic:
        return ChunkDiagnostic(
            chunk_id=candidate.chunk.chunk_id,
            document_id=candidate.chunk.document_id,
            semantic_score=candidate.semantic_score,
            lexical_score=candidate.lexical_score,
            phrase_match=candidate.phrase_match,
            final_score=candidate.final_score,
            rank_before=candidate.rank_before,
            rank_after=candidate.rank_after,
        )

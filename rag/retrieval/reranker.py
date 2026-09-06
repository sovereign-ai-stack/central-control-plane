"""Deterministic lexical/phrase reranking over semantic candidates."""

from __future__ import annotations

from rag.retrieval.config import RetrievalConfig
from rag.retrieval.lexical import phrase_match_score, token_overlap_score
from rag.retrieval.ranking import rank_by_similarity
from rag.retrieval.types import RankedCandidate, SemanticCandidate


class Ranker:
    """
    final_score =
        semantic_weight * semantic_score
        + lexical_weight * lexical_score
        + phrase_weight * phrase_match
    """

    def __init__(self, config: RetrievalConfig) -> None:
        self._config = config

    def rerank(self, query: str, candidates: list[SemanticCandidate]) -> list[RankedCandidate]:
        ranked_inputs: list[tuple[SemanticCandidate, float, object]] = []
        for candidate in candidates:
            lexical = token_overlap_score(query, candidate.chunk.content)
            phrase = phrase_match_score(query, candidate.chunk.content)
            final = (
                self._config.semantic_weight * candidate.semantic_score
                + self._config.lexical_weight * lexical
                + self._config.phrase_weight * phrase
            )
            ranked_inputs.append((candidate, final, candidate.chunk.chunk_id))

        ordered = rank_by_similarity(
            [(item[0], item[1], item[2]) for item in ranked_inputs],
            top_k=len(ranked_inputs),
        )

        results: list[RankedCandidate] = []
        for rank_after, (candidate, final_score, _chunk_id) in enumerate(ordered, start=1):
            lexical = token_overlap_score(query, candidate.chunk.content)
            phrase = phrase_match_score(query, candidate.chunk.content)
            results.append(
                RankedCandidate(
                    chunk=candidate.chunk,
                    semantic_score=candidate.semantic_score,
                    lexical_score=lexical,
                    phrase_match=phrase,
                    final_score=final_score,
                    rank_before=candidate.rank_before,
                    rank_after=rank_after,
                )
            )
        return results

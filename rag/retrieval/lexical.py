"""Persian-aware lexical scoring for reranking."""

from __future__ import annotations

import re

from rag.ingestion.persian import normalize_persian

_TOKEN_SPLIT = re.compile(r"\s+")


def normalized_tokens(text: str) -> frozenset[str]:
    normalized = normalize_persian(text)
    return frozenset(token for token in _TOKEN_SPLIT.split(normalized) if token)


def token_overlap_score(query: str, content: str) -> float:
    """
    overlap = |query_tokens ∩ document_tokens| / |query_tokens|

    Returns 0.0 when query has no tokens after normalization.
    """
    query_tokens = normalized_tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = normalized_tokens(content)
    return len(query_tokens & content_tokens) / len(query_tokens)


def phrase_match_score(query: str, content: str) -> float:
    """1.0 when normalized query is a substring of normalized content, else 0.0."""
    normalized_query = normalize_persian(query).strip()
    if not normalized_query:
        return 0.0
    normalized_content = normalize_persian(content)
    return 1.0 if normalized_query in normalized_content else 0.0

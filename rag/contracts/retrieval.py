"""Retrieval contract types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from rag.authorization.context import AuthorizationContext, require_authorization_context


@dataclass(frozen=True, slots=True)
class RetrievalOptions:
    top_k: int = 10
    candidate_k: int | None = None
    include_diagnostics: bool = False


@dataclass(frozen=True, slots=True)
class RetrievedContextSummary:
    text: str
    char_count: int
    truncated: bool


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    company_id: UUID
    department_id: UUID
    content: str
    score: float
    chunk_index: int
    document_version: int


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunks: tuple[Any, ...]
    context: RetrievedContextSummary | None = None


class SecureRetriever(Protocol):
    """Canonical retrieval contract — filters derived from AuthorizationContext only."""

    def search(
        self,
        query: str,
        authorization_context: AuthorizationContext,
        options: RetrievalOptions | None = None,
    ) -> RetrievalResult:
        ...


class AuthGuardedStubRetriever:
    """
    Phase 1 stub proving the retrieval contract enforces AuthorizationContext.
    Does not call vector store or embedding layers.
    """

    def search(
        self,
        query: str,
        authorization_context: AuthorizationContext | None = None,
        options: RetrievalOptions | None = None,
        **kwargs: object,
    ) -> RetrievalResult:
        if kwargs:
            raise TypeError(
                "SecureRetriever.search() does not accept caller-supplied filter kwargs"
            )
        authz = require_authorization_context(authorization_context)
        _ = query, options, authz
        return RetrievalResult(chunks=())

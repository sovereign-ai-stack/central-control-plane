"""
L4 authorization re-validation (spec 005 SR-PP-004, PP-061; 004 defense-in-depth).

This is a defense-in-depth check, not the primary control: scope was already
enforced server-side at retrieval. It re-verifies every candidate against the
resolved `AuthorizationContext` *before* reranking and context assembly, so a
storage or wiring regression cannot leak a chunk into the context envelope.

It only ever narrows the candidate set. It never constructs scope, never widens
it, and never consults caller input.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from rag.authorization.context import AuthorizationContext
from rag.contracts.retrieval import RetrievedChunk
from rag.pipeline.errors import UnauthorizedChunkInPipelineError


class CandidateAuthorizationValidator:
    """
    Strips chunks outside the caller's company/department scope.

    strict=False (default): drop unauthorized chunks and report their IDs.
    strict=True: fail closed on first detection, returning no chunks at all.
    Neither mode ever exposes unauthorized chunk content.
    """

    def __init__(self, *, strict: bool = False) -> None:
        self._strict = strict

    @property
    def strict(self) -> bool:
        return self._strict

    def validate(
        self,
        candidates: Sequence[RetrievedChunk],
        authorization_context: AuthorizationContext,
    ) -> tuple[tuple[RetrievedChunk, ...], tuple[UUID, ...]]:
        allowed_departments = set(authorization_context.allowed_department_ids)
        authorized: list[RetrievedChunk] = []
        blocked: list[UUID] = []

        for chunk in candidates:
            if (
                chunk.company_id == authorization_context.company_id
                and chunk.department_id in allowed_departments
            ):
                authorized.append(chunk)
                continue
            blocked.append(chunk.chunk_id)

        if blocked and self._strict:
            raise UnauthorizedChunkInPipelineError(
                f"{len(blocked)} unauthorized chunk(s) detected in pipeline input"
            )
        return tuple(authorized), tuple(blocked)

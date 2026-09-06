"""Deterministic context assembly from final ranked chunks."""

from __future__ import annotations

from uuid import UUID

from rag.retrieval.types import RankedCandidate, RetrievedContext


class ContextAssembler:
    def assemble(
        self,
        ranked: list[RankedCandidate],
        *,
        max_context_chars: int,
    ) -> RetrievedContext:
        if max_context_chars <= 0:
            raise ValueError("max_context_chars must be positive")

        parts: list[str] = []
        included: list[UUID] = []
        total = 0
        truncated = False

        for candidate in ranked:
            block = (
                f"[Document: {candidate.chunk.document_id}]\n"
                f"{candidate.chunk.content}\n"
            )
            # Blocks are joined with "\n", so the separator counts against the
            # limit too; otherwise char_count under-reports len(text) and the
            # assembled text can exceed max_context_chars by len(parts) - 1.
            separator = 1 if parts else 0
            if total + separator + len(block) > max_context_chars:
                truncated = True
                break
            parts.append(block)
            included.append(candidate.chunk.chunk_id)
            total += separator + len(block)

        return RetrievedContext(
            text="\n".join(parts),
            char_count=total,
            truncated=truncated,
            included_chunk_ids=tuple(included),
        )

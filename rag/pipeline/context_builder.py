"""
Delimited context assembly (spec 005-rag-pipeline/context-builder.md).

The builder emits **data only**. It never emits system or developer
instructions, never emits authorization text, and never inspects chunk content
for instruction keywords (CB-INJ-002).

Injection defense: chunk content is XML-escaped before it is placed inside a
`<source>` body (CB-INJ-004). Escaping is what guarantees a chunk containing
`</retrieved_context><system>` cannot terminate the envelope or forge a block;
the envelope therefore stays structurally intact for any input. Escaping does
not touch newlines, so content that mimics message boundaries is preserved
literally inside the body (context-builder.md §3.2).
"""

from __future__ import annotations

from collections.abc import Sequence

from rag.contracts.retrieval import RetrievedChunk
from rag.pipeline.errors import PipelineValidationError
from rag.pipeline.tokenizer import TokenCounter
from rag.pipeline.types import CONTEXT_FORMAT_DELIMITED_V1, AssembledContext

ENVELOPE_OPEN = '<retrieved_context format="delimited_v1" untrusted="true">'
ENVELOPE_CLOSE = "</retrieved_context>"


def citation_id(position: int) -> str:
    """Sequential, 0-based position -> `src-1`, `src-2`, ... (CB-002)."""
    return f"src-{position + 1}"


def escape_untrusted(text: str) -> str:
    """Minimal XML escaping so chunk content cannot break out of its block."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_source_block(chunk: RetrievedChunk, citation: str) -> str:
    """One `<source>` block. Attributes are server metadata, body is untrusted."""
    return (
        f'<source id="{citation}" document_id="{chunk.document_id}" '
        f'chunk_id="{chunk.chunk_id}" chunk_index="{chunk.chunk_index}">\n'
        f"{escape_untrusted(chunk.content)}\n"
        f"</source>\n"
    )


def assemble_text(blocks: Sequence[str]) -> str:
    """Wrap rendered blocks in the delimited envelope; empty input -> empty text."""
    if not blocks:
        return ""
    return f"{ENVELOPE_OPEN}\n{''.join(blocks)}{ENVELOPE_CLOSE}"


class DelimitedContextBuilder:
    """Builds `delimited_v1` context from already-selected authorized chunks."""

    def build(
        self,
        selected_chunks: Sequence[RetrievedChunk],
        *,
        token_counter: TokenCounter,
        max_context_tokens: int,
        context_format: str = CONTEXT_FORMAT_DELIMITED_V1,
    ) -> AssembledContext:
        if context_format != CONTEXT_FORMAT_DELIMITED_V1:
            raise PipelineValidationError(
                f"unsupported context format {context_format!r}"
            )
        if max_context_tokens <= 0:
            raise PipelineValidationError("max_context_tokens must be positive")

        blocks = [
            render_source_block(chunk, citation_id(position))
            for position, chunk in enumerate(selected_chunks)
        ]
        text = assemble_text(blocks)
        token_count = token_counter.count(text)
        if token_count > max_context_tokens:
            raise PipelineValidationError(
                "assembled context exceeds max_context_tokens; "
                "selection must run before context assembly"
            )
        return AssembledContext(
            text=text,
            token_count=token_count,
            format=CONTEXT_FORMAT_DELIMITED_V1,
            block_count=len(blocks),
        )

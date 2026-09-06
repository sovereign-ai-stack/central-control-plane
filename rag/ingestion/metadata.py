"""Build chunk records with mandatory security metadata and optional enrichment."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from rag.ingestion.errors import IngestPipelineError
from rag.ingestion.extraction.types import SourceSegment
from rag.ingestion.source_position import resolve_position
from rag.ingestion.types import ChunkDraft, DocumentStatus, StoredChunk
from rag.ingestion.validation import chunk_content_hash
from rag.nlp.pipeline import PersianNlpPipeline
from rag.nlp.sentences import BlockKind, classify_line
from rag.nlp.tokenizer import count_tokens


def build_stored_chunks(
    drafts: list[ChunkDraft],
    *,
    document_id: UUID,
    company_id: UUID,
    department_id: UUID,
    document_version: int,
    nlp: PersianNlpPipeline | None = None,
    segments: Sequence[SourceSegment] = (),
    language: str | None = None,
    original_text: str | None = None,
) -> list[StoredChunk]:
    if not drafts:
        raise IngestPipelineError("chunker produced zero chunks")

    chunks: list[StoredChunk] = []
    for draft in drafts:
        position = resolve_position(draft.char_start, draft.char_end, segments)
        chunk = StoredChunk(
            chunk_id=uuid4(),
            document_id=document_id,
            company_id=company_id,
            department_id=department_id,
            document_version=document_version,
            chunk_index=draft.chunk_index,
            content=draft.content,
            content_hash=chunk_content_hash(draft.content),
            token_count=_token_count(draft.content, nlp),
            original_text=_slice_original(original_text, draft),
            embedding_text=_embedding_text(draft.content, nlp),
            nlp_version=nlp.version if nlp is not None else None,
            language=language,
            section_path=_section_path(draft.content),
            char_start=draft.char_start,
            char_end=draft.char_end,
            source_segment_label=position.label,
            source_segment_start=position.start_ordinal,
            source_segment_end=position.end_ordinal,
            # Written non-searchable; the pipeline flips this to INDEXED
            # only once persistence succeeds.
            document_status=DocumentStatus.PROCESSING.value,
        )
        _validate_chunk_security(chunk)
        chunks.append(chunk)
    return chunks


def _token_count(content: str, nlp: PersianNlpPipeline | None) -> int:
    # Word-token count; falls back to the legacy whitespace split only when the
    # NLP layer is absent so pre-Phase-5 counts stay comparable.
    if nlp is None:
        return len(content.split())
    return count_tokens(content)


def _embedding_text(content: str, nlp: PersianNlpPipeline | None) -> str | None:
    if nlp is None:
        return None
    processed = nlp.embedding_text(content)
    return processed if processed != content else None


def _slice_original(original_text: str | None, draft: ChunkDraft) -> str | None:
    """
    Best-effort slice of the pre-normalization source for this chunk.

    Offsets index normalized text, so this is only recorded when the source and
    normalized forms are the same length; otherwise a wrong slice would be worse
    than none.
    """
    if original_text is None:
        return None
    if draft.char_end > len(original_text):
        return None
    return original_text[draft.char_start : draft.char_end]


def _section_path(content: str) -> str | None:
    """The leading heading of a chunk, when it starts with one."""
    first_line = content.split("\n", 1)[0].strip()
    if not first_line:
        return None
    if classify_line(first_line) is BlockKind.HEADING:
        return first_line
    return None


def _validate_chunk_security(chunk: StoredChunk) -> None:
    required = (
        chunk.chunk_id,
        chunk.document_id,
        chunk.company_id,
        chunk.department_id,
    )
    if any(value is None for value in required):
        raise IngestPipelineError("chunk missing mandatory security metadata")

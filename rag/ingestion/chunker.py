"""Document chunking for plain text."""

from __future__ import annotations

from rag.ingestion.types import ChunkDraft

DEFAULT_MAX_CHUNK_CHARS = 800


def chunk_text(text: str, max_chars: int = DEFAULT_MAX_CHUNK_CHARS) -> list[ChunkDraft]:
    if not text.strip():
        return []

    drafts: list[ChunkDraft] = []
    paragraphs = text.split("\n\n")
    buffer = ""
    char_cursor = 0
    chunk_index = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            char_cursor += 2
            continue

        candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
        if len(candidate) <= max_chars:
            buffer = candidate
            continue

        if buffer:
            start = char_cursor - len(buffer)
            drafts.append(
                ChunkDraft(
                    chunk_index=chunk_index,
                    content=buffer,
                    char_start=max(start, 0),
                    char_end=char_cursor,
                )
            )
            chunk_index += 1
            buffer = ""

        while len(paragraph) > max_chars:
            split_at = _find_split_point(paragraph, max_chars)
            piece = paragraph[:split_at].strip()
            if piece:
                drafts.append(
                    ChunkDraft(
                        chunk_index=chunk_index,
                        content=piece,
                        char_start=char_cursor,
                        char_end=char_cursor + len(piece),
                    )
                )
                chunk_index += 1
            paragraph = paragraph[split_at:].strip()
            char_cursor += split_at

        buffer = paragraph
        char_cursor += len(paragraph) + 2

    if buffer.strip():
        drafts.append(
            ChunkDraft(
                chunk_index=chunk_index,
                content=buffer.strip(),
                char_start=max(char_cursor - len(buffer), 0),
                char_end=char_cursor,
            )
        )

    return drafts


def _find_split_point(text: str, max_chars: int) -> int:
    window = text[:max_chars]
    for separator in (". ", "؟ ", "؛ ", "\n", " "):
        idx = window.rfind(separator)
        if idx > max_chars // 2:
            return idx + len(separator)
    return max_chars

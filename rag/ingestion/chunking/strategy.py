"""Chunking strategy contract and the legacy character-based implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag.ingestion.chunker import chunk_text
from rag.ingestion.chunking.config import ChunkingConfig
from rag.ingestion.types import ChunkDraft


@runtime_checkable
class ChunkingStrategy(Protocol):
    """Splits normalized document text into ordered chunk drafts."""

    @property
    def name(self) -> str:
        ...

    def split(self, text: str) -> list[ChunkDraft]:
        ...


class FixedCharChunker:
    """
    Pre-Phase-5 behaviour: paragraph-aware splitting on a character budget.

    Kept as the default so existing corpora keep chunking identically until
    semantic chunking is explicitly selected.
    """

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    @property
    def name(self) -> str:
        return "fixed_char"

    def split(self, text: str) -> list[ChunkDraft]:
        return chunk_text(text, max_chars=self._config.max_chars)

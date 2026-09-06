"""Chunker unit tests."""

from __future__ import annotations

from rag.ingestion.chunker import chunk_text


class TestChunker:
    def test_produces_multiple_chunks_for_long_text(self):
        text = "پاراگراف اول.\n\n" + ("جمله تست. " * 200)
        chunks = chunk_text(text, max_chars=200)
        assert len(chunks) > 1
        assert all(chunk.content.strip() for chunk in chunks)

    def test_empty_text_returns_empty(self):
        assert chunk_text("   ") == []

    def test_chunk_indices_sequential(self):
        text = "بخش اول. " * 50 + "\n\n" + "بخش دوم. " * 50
        chunks = chunk_text(text, max_chars=100)
        indices = [chunk.chunk_index for chunk in chunks]
        assert indices == list(range(len(chunks)))

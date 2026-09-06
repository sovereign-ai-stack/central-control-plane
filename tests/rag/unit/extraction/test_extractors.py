"""
Unit tests for the document extraction layer (Phase 5A).

Covers the generic contract, the plain-text adapter, the PDF adapter, and
registry selection.
"""

from __future__ import annotations

import pytest
from tests.rag.pdf_fixtures import (
    build_corrupt_pdf,
    build_encrypted_pdf,
    build_image_only_pdf,
    build_pdf,
    build_persian_pdf,
)

from rag.ingestion.extraction import (
    SOURCE_TYPE_PDF,
    SOURCE_TYPE_TEXT,
    CorruptDocumentError,
    DocumentExtractor,
    EmptyDocumentError,
    ExtractionLimitError,
    ExtractionLimits,
    ExtractorRegistry,
    PdfExtractor,
    PlainTextExtractor,
    UnsupportedSourceTypeError,
    extract_from_string,
)
from rag.ingestion.extraction.types import ExtractedDocument, SourceSegment


class TestPlainTextExtractor:
    def test_extracts_utf8_text(self):
        document = PlainTextExtractor().extract(
            "متن نمونه فارسی".encode(), filename="doc.txt"
        )
        assert document.text == "متن نمونه فارسی"
        assert document.source_type == SOURCE_TYPE_TEXT
        assert document.filename == "doc.txt"

    def test_single_segment_spans_whole_document(self):
        text = "خط اول\nخط دوم"
        document = PlainTextExtractor().extract(text.encode())
        assert document.segment_count == 1
        segment = document.segments[0]
        assert segment.label == "document"
        assert segment.ordinal == 1
        assert (segment.char_start, segment.char_end) == (0, len(text))

    def test_strips_bom(self):
        document = PlainTextExtractor().extract("﻿سلام".encode())
        assert document.text == "سلام"

    def test_invalid_utf8_rejected(self):
        with pytest.raises(CorruptDocumentError):
            PlainTextExtractor().extract(b"\xff\xfe\x00invalid")

    def test_blank_document_rejected(self):
        with pytest.raises(EmptyDocumentError):
            PlainTextExtractor().extract(b"   \n\n  ")

    def test_oversized_file_rejected(self):
        limits = ExtractionLimits(max_file_bytes=10)
        with pytest.raises(ExtractionLimitError):
            PlainTextExtractor(limits).extract(b"x" * 11)

    def test_extract_from_string_helper(self):
        document = extract_from_string("سلام دنیا")
        assert document.text == "سلام دنیا"
        assert document.source_type == SOURCE_TYPE_TEXT


class TestPdfExtractor:
    def test_extracts_text_from_single_page(self):
        document = PdfExtractor().extract(build_pdf(["Hello page one"]), filename="a.pdf")
        assert "Hello page one" in document.text
        assert document.source_type == SOURCE_TYPE_PDF
        assert document.page_count == 1

    def test_page_segments_carry_ordinals(self):
        document = PdfExtractor().extract(build_pdf(["first page", "second page"]))
        assert document.page_count == 2
        assert [segment.ordinal for segment in document.segments] == [1, 2]
        assert all(segment.label == "page" for segment in document.segments)

    def test_segment_offsets_map_back_to_page_text(self):
        document = PdfExtractor().extract(build_pdf(["alpha text", "beta text"]))
        first, second = document.segments
        assert "alpha" in document.text[first.char_start : first.char_end]
        assert "beta" in document.text[second.char_start : second.char_end]
        assert first.char_end <= second.char_start

    def test_persian_text_extracted_in_logical_order(self):
        expected = "مرخصی سالانه کارکنان"
        document = PdfExtractor().extract(build_persian_pdf([expected]))
        assert expected in document.text

    def test_document_metadata_captured(self):
        document = PdfExtractor().extract(build_pdf(["body"], title="راهنمای منابع انسانی"))
        assert document.metadata.get("title") == "راهنمای منابع انسانی"

    def test_blank_pages_do_not_shift_later_page_numbers(self):
        document = PdfExtractor().extract(build_pdf(["", "real content", ""]))
        assert document.page_count == 3
        assert [segment.ordinal for segment in document.segments] == [2]

    def test_corrupt_pdf_rejected(self):
        with pytest.raises(CorruptDocumentError):
            PdfExtractor().extract(build_corrupt_pdf())

    def test_encrypted_pdf_rejected(self):
        with pytest.raises(CorruptDocumentError):
            PdfExtractor().extract(build_encrypted_pdf())

    def test_non_pdf_bytes_rejected(self):
        with pytest.raises(CorruptDocumentError):
            PdfExtractor().extract(b"just some plain text")

    def test_image_only_pdf_reported_as_empty(self):
        # No OCR in scope: a scan-only PDF must fail loudly, not silently index nothing.
        with pytest.raises(EmptyDocumentError):
            PdfExtractor().extract(build_image_only_pdf())

    def test_page_limit_enforced(self):
        limits = ExtractionLimits(max_pages=1)
        with pytest.raises(ExtractionLimitError):
            PdfExtractor(limits).extract(build_pdf(["one", "two"]))

    def test_file_size_limit_enforced(self):
        limits = ExtractionLimits(max_file_bytes=32)
        with pytest.raises(ExtractionLimitError):
            PdfExtractor(limits).extract(build_pdf(["padding text"]))

    def test_errors_do_not_leak_parser_internals(self):
        with pytest.raises(CorruptDocumentError) as exc_info:
            PdfExtractor().extract(build_corrupt_pdf())
        message = str(exc_info.value)
        assert "Traceback" not in message
        assert "pypdf" not in message.lower()


class TestExtractorProtocol:
    def test_both_adapters_satisfy_the_protocol(self):
        assert isinstance(PlainTextExtractor(), DocumentExtractor)
        assert isinstance(PdfExtractor(), DocumentExtractor)

    def test_extracted_document_carries_no_format_specific_fields(self):
        # Downstream layers must never see PDF vocabulary beyond source_type.
        fields = set(ExtractedDocument.__dataclass_fields__)
        assert fields == {
            "text",
            "source_type",
            "filename",
            "metadata",
            "segments",
            "page_count",
        }
        assert "page" not in set(SourceSegment.__dataclass_fields__)


class TestExtractorRegistry:
    def test_selects_pdf_by_content_sniffing(self):
        registry = ExtractorRegistry()
        extractor = registry.select(build_pdf(["x"]), filename=None)
        assert extractor.source_type == SOURCE_TYPE_PDF

    def test_content_wins_over_misleading_filename(self):
        registry = ExtractorRegistry()
        extractor = registry.select(build_pdf(["x"]), filename="actually.txt")
        assert extractor.source_type == SOURCE_TYPE_PDF

    def test_falls_back_to_plain_text(self):
        registry = ExtractorRegistry()
        extractor = registry.select("سلام".encode(), filename="notes.txt")
        assert extractor.source_type == SOURCE_TYPE_TEXT

    def test_explicit_source_type_is_honoured(self):
        registry = ExtractorRegistry()
        extractor = registry.select(b"anything", source_type=SOURCE_TYPE_TEXT)
        assert extractor.source_type == SOURCE_TYPE_TEXT

    def test_unknown_source_type_rejected(self):
        with pytest.raises(UnsupportedSourceTypeError):
            ExtractorRegistry().select(b"x", source_type="docx")

    def test_undecodable_unknown_format_rejected(self):
        with pytest.raises(UnsupportedSourceTypeError):
            ExtractorRegistry().select(b"\xff\xfe\x00\x01binary", filename="a.bin")

    def test_extract_delegates_to_selected_adapter(self):
        registry = ExtractorRegistry()
        document = registry.extract(build_pdf(["routed"]), filename="doc.pdf")
        assert "routed" in document.text
        assert document.source_type == SOURCE_TYPE_PDF

    def test_new_format_needs_only_a_new_adapter(self):
        class MarkdownExtractor:
            source_type = "markdown"
            supported_extensions = (".md",)

            def sniff(self, data: bytes) -> bool:
                return data.startswith(b"# ")

            def extract(self, data: bytes, *, filename: str | None = None):
                text = data.decode("utf-8")
                return ExtractedDocument(
                    text=text,
                    source_type="markdown",
                    filename=filename,
                    segments=(
                        SourceSegment(
                            label="document", ordinal=1, char_start=0, char_end=len(text)
                        ),
                    ),
                )

        registry = ExtractorRegistry()
        registry.register(MarkdownExtractor())
        document = registry.extract(b"# Title\n\nbody", filename="readme.md")
        assert document.source_type == "markdown"
        assert "Title" in document.text

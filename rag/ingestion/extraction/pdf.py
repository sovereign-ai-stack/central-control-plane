"""
PDF text extractor.

Scope (deliberately narrow): text extraction, page-number provenance, and
invalid-file handling. No OCR, no table reconstruction, no layout analysis — a
scanned image-only PDF is reported as empty rather than silently returning
nothing useful.

`pypdf` is imported lazily so the rest of ingestion keeps working (and the test
suite keeps running) in an environment where it is unavailable.
"""

from __future__ import annotations

import io
import re
from typing import Any
import unicodedata

from rag.ingestion.extraction.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    ExtractionError,
)
from rag.ingestion.extraction.limits import Deadline, ExtractionLimits
from rag.ingestion.extraction.types import (
    SEGMENT_LABEL_PAGE,
    SOURCE_TYPE_PDF,
    ExtractedDocument,
    SourceSegment,
)

PDF_MAGIC = b"%PDF-"
_PAGE_SEPARATOR = "\n\n"
_METADATA_FIELDS = {
    "/Title": "title",
    "/Author": "author",
    "/Subject": "subject",
    "/Creator": "creator",
    "/Producer": "producer",
}

_PERSIAN_CHAR_MAP = str.maketrans({
    "\u064a": "\u06cc",  # arabic yeh -> persian yeh
    "\u0649": "\u06cc",  # alef maksura -> persian yeh
    "\u0643": "\u06a9",  # arabic kaf -> persian kaf
    "\u0629": "\u0647",  # teh marbuta -> heh
    "\u0640": "",        # tatweel
    "\u200b": "",        # zero width space
    "\ufeff": "",        # BOM
})

_REPEATED_LETTERS = re.compile(r"([بتثجچحخدذرزژسشصضطظعغفقکگلمنهی])\1{2,}")

_CORRUPT_GLYPH_FIXES = [
    (re.compile(r"\bسرمايهدذارى\b"), "سرمایه‌گذاری"),
    (re.compile(r"\bسرمايهدذاری\b"), "سرمایه‌گذاری"),
    (re.compile(r"\bسرمایه\s*دذاری\b"), "سرمایه‌گذاری"),
    (re.compile(r"\bاستارتاب\b"), "استارتاپ"),
    (re.compile(r"\bمنتورينك\b"), "منتورینگ"),
    (re.compile(r"\bمنتورینک\b"), "منتورینگ"),
    (re.compile(r"\bزيرسااتى\b"), "زیرساختی"),
    (re.compile(r"\bزیرسااتی\b"), "زیرساختی"),
    (re.compile(r"\bادمات\b"), "خدمات"),
    (re.compile(r"\bيوست\b"), "پیوست"),
    (re.compile(r"\bدرس اب\b"), "در سهام"),
    (re.compile(r"\bباناب ااترارى\b"), "با نام تجاری"),
]


def clean_persian_pdf_text(text: str) -> str:
    """Repairs common Persian PDF font encoding artifacts and presentation forms."""
    if not text:
        return ""
    # 1. Normalize Unicode compatibility decomposition (folds presentation forms like ﻼ, ﻴ, ﺘ)
    t = unicodedata.normalize("NFKC", text)
    # 2. Map Arabic yeh/kaf/tatweel
    t = t.translate(_PERSIAN_CHAR_MAP)
    # 3. Collapse repeated tatweel letters (e.g. استتتتارت -> استارت, شتتتود -> شود)
    t = _REPEATED_LETTERS.sub(r"\1", t)
    # 4. Apply known font encoding repair patterns
    for pattern, replacement in _CORRUPT_GLYPH_FIXES:
        t = pattern.sub(replacement, t)
    return t


def pymupdf_available() -> bool:
    try:
        import fitz  # noqa: F401
    except ImportError:
        return False
    return True


def pypdf_available() -> bool:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return False
    return True


def _load_pypdf() -> Any:
    try:
        import pypdf
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ExtractionError("PDF support is not available") from exc
    return pypdf


class PdfExtractor:
    """Extracts per-page text from a PDF, one `SourceSegment` per page."""

    def __init__(self, limits: ExtractionLimits | None = None) -> None:
        self._limits = limits or ExtractionLimits()

    @property
    def source_type(self) -> str:
        return SOURCE_TYPE_PDF

    @property
    def supported_extensions(self) -> tuple[str, ...]:
        return (".pdf",)

    def sniff(self, data: bytes) -> bool:
        return data.startswith(PDF_MAGIC)

    def extract(
        self,
        data: bytes,
        *,
        filename: str | None = None,
        deadline: Deadline | None = None,
    ) -> ExtractedDocument:
        self._limits.check_file_size(len(data))
        if not self.sniff(data):
            raise CorruptDocumentError("file is not a PDF document")

        budget = deadline or Deadline(self._limits.timeout_seconds)

        # 1. High-fidelity PyMuPDF extraction if available
        if pymupdf_available():
            try:
                import fitz
                doc = fitz.open(stream=data, filetype="pdf")
                if doc.is_encrypted:
                    raise CorruptDocumentError("encrypted PDF documents are not supported")
                pages_count = len(doc)
                self._limits.check_page_count(pages_count)
                parts: list[str] = []
                segments: list[SourceSegment] = []
                cursor = 0
                for ordinal in range(1, pages_count + 1):
                    budget.check()
                    page = doc[ordinal - 1]
                    raw_text = page.get_text("text") or ""
                    page_text = clean_persian_pdf_text(raw_text)
                    if not page_text.strip():
                        continue
                    separator = len(_PAGE_SEPARATOR) if parts else 0
                    self._limits.check_extracted_chars(cursor + separator + len(page_text))
                    if parts:
                        cursor += len(_PAGE_SEPARATOR)
                        parts.append(_PAGE_SEPARATOR)
                    start = cursor
                    parts.append(page_text)
                    cursor += len(page_text)
                    segments.append(
                        SourceSegment(
                            label=SEGMENT_LABEL_PAGE,
                            ordinal=ordinal,
                            char_start=start,
                            char_end=cursor,
                        )
                    )
                text = "".join(parts)
                if text.strip():
                    metadata = {}
                    for k, v in (doc.metadata or {}).items():
                        norm_k = f"/{k.capitalize()}"
                        if isinstance(v, str) and v.strip() and norm_k in _METADATA_FIELDS:
                            metadata[_METADATA_FIELDS[norm_k]] = v.strip()
                    return ExtractedDocument(
                        text=text,
                        source_type=SOURCE_TYPE_PDF,
                        filename=filename,
                        metadata=metadata,
                        segments=tuple(segments),
                        page_count=pages_count,
                    )
            except CorruptDocumentError:
                raise
            except Exception:
                # If PyMuPDF extraction failed unexpectedly, fallback to pypdf below
                pass

        # 2. Standard pypdf extraction fallback
        pypdf = _load_pypdf()
        reader = self._open_reader(pypdf, data)
        pages = self._page_list(reader)
        self._limits.check_page_count(len(pages))

        parts: list[str] = []
        segments: list[SourceSegment] = []
        cursor = 0
        for ordinal, page in enumerate(pages, start=1):
            # Cooperative cancellation: a slow document stops doing work at the
            # next page rather than merely being abandoned by the caller.
            budget.check()
            page_text = self._page_text(page)
            if not page_text.strip():
                # Keep the page in the ordinal sequence but contribute no span,
                # so later pages still report their true page number.
                continue
            separator = len(_PAGE_SEPARATOR) if parts else 0
            # Check the *projected* size before materialising the page, so one
            # enormous page cannot be fully accumulated before the limit fires.
            self._limits.check_extracted_chars(cursor + separator + len(page_text))

            if parts:
                cursor += len(_PAGE_SEPARATOR)
                parts.append(_PAGE_SEPARATOR)
            start = cursor
            parts.append(page_text)
            cursor += len(page_text)
            segments.append(
                SourceSegment(
                    label=SEGMENT_LABEL_PAGE,
                    ordinal=ordinal,
                    char_start=start,
                    char_end=cursor,
                )
            )

        text = "".join(parts)
        if not text.strip():
            raise EmptyDocumentError(
                "PDF contains no extractable text (it may be image-only)"
            )

        return ExtractedDocument(
            text=text,
            source_type=SOURCE_TYPE_PDF,
            filename=filename,
            metadata=self._document_metadata(reader),
            segments=tuple(segments),
            page_count=len(pages),
        )

    @staticmethod
    def _open_reader(pypdf: Any, data: bytes) -> Any:
        try:
            reader = pypdf.PdfReader(io.BytesIO(data))
        except Exception as exc:
            raise CorruptDocumentError("PDF document could not be parsed") from exc
        if getattr(reader, "is_encrypted", False):
            raise CorruptDocumentError("encrypted PDF documents are not supported")
        return reader

    @staticmethod
    def _page_list(reader: Any) -> list[Any]:
        try:
            return list(reader.pages)
        except Exception as exc:
            raise CorruptDocumentError("PDF page tree could not be read") from exc

    @staticmethod
    def _page_text(page: Any) -> str:
        try:
            raw = page.extract_text() or ""
            return clean_persian_pdf_text(raw)
        except Exception:  # noqa: BLE001 - pypdf raises arbitrary types per malformed page
            # A single unreadable page must not fail the whole document.
            return ""

    @staticmethod
    def _document_metadata(reader: Any) -> dict[str, str]:
        try:
            raw = reader.metadata or {}
        except Exception:  # noqa: BLE001 - metadata is optional; never fail extraction for it
            return {}
        metadata: dict[str, str] = {}
        for key, name in _METADATA_FIELDS.items():
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                metadata[name] = value.strip()
        return metadata

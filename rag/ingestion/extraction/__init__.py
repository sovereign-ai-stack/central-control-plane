"""Format-agnostic document extraction adapters."""

from rag.ingestion.extraction.errors import (
    CorruptDocumentError,
    EmptyDocumentError,
    ExtractionError,
    ExtractionLimitError,
    UnsupportedSourceTypeError,
)
from rag.ingestion.extraction.limits import ExtractionLimits
from rag.ingestion.extraction.pdf import PdfExtractor, pypdf_available
from rag.ingestion.extraction.plain_text import PlainTextExtractor, extract_from_string
from rag.ingestion.extraction.protocol import DocumentExtractor
from rag.ingestion.extraction.registry import ExtractorRegistry, default_extractors
from rag.ingestion.extraction.types import (
    SOURCE_TYPE_PDF,
    SOURCE_TYPE_TEXT,
    ExtractedDocument,
    SourceSegment,
)

__all__ = [
    "SOURCE_TYPE_PDF",
    "SOURCE_TYPE_TEXT",
    "CorruptDocumentError",
    "DocumentExtractor",
    "EmptyDocumentError",
    "ExtractedDocument",
    "ExtractionError",
    "ExtractionLimitError",
    "ExtractionLimits",
    "ExtractorRegistry",
    "PdfExtractor",
    "PlainTextExtractor",
    "SourceSegment",
    "UnsupportedSourceTypeError",
    "default_extractors",
    "extract_from_string",
    "pypdf_available",
]

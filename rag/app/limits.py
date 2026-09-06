"""
Request input limits.

Bounds on what a caller may submit, enforced at the API boundary before any
expensive work. Distinct from rate limiting: that bounds how *often* a caller
may ask, this bounds how *large* a single ask may be.

The gap this closes: `query` was only checked for emptiness, so a multi-megabyte
query would be normalized, tokenized, morphologically processed, and embedded
before anything noticed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Generous for a real question in any language, far below anything that costs
# meaningful CPU to normalize and embed.
DEFAULT_MAX_QUERY_CHARS = 4_000


@dataclass(frozen=True, slots=True)
class RequestLimits:
    max_query_chars: int = DEFAULT_MAX_QUERY_CHARS

    def validate(self) -> None:
        from rag.app.errors import ApiValidationError

        if self.max_query_chars <= 0:
            raise ApiValidationError("max_query_chars must be positive")

    def check_query(self, query: str) -> None:
        """
        Reject an oversized query before it reaches the NLP or embedding layers.

        Measured in characters rather than bytes: the downstream cost is
        per-character (normalization, tokenization, morphology), and a byte
        limit would silently penalise Persian, whose characters are multi-byte
        in UTF-8.
        """
        from rag.app.errors import ApiPayloadTooLargeError

        if len(query) > self.max_query_chars:
            raise ApiPayloadTooLargeError(
                f"query exceeds the maximum of {self.max_query_chars} characters"
            )


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_extraction_limits(path: Path | None = None):
    """
    Extraction limits from the same input-limits file.

    Kept beside the query limit because both answer one question: how much may a
    single request cost us?
    """
    from rag.ingestion.extraction.limits import ExtractionLimits

    config_path = path or _repo_root() / "config" / "api_limits.yaml"
    if not config_path.exists():
        return ExtractionLimits()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return ExtractionLimits()
    block = raw.get("api_limits", raw)
    if not isinstance(block, dict):
        return ExtractionLimits()
    extraction = block.get("extraction", {})
    if not isinstance(extraction, dict):
        return ExtractionLimits()

    defaults = ExtractionLimits()
    return ExtractionLimits(
        max_file_bytes=int(extraction.get("max_file_bytes", defaults.max_file_bytes)),
        max_pages=int(extraction.get("max_pages", defaults.max_pages)),
        max_extracted_chars=int(
            extraction.get("max_extracted_chars", defaults.max_extracted_chars)
        ),
        timeout_seconds=float(
            extraction.get("timeout_seconds", defaults.timeout_seconds)
        ),
    )


def load_request_limits(path: Path | None = None) -> RequestLimits:
    config_path = path or _repo_root() / "config" / "api_limits.yaml"
    if not config_path.exists():
        return RequestLimits()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return RequestLimits()
    block = raw.get("api_limits", raw)
    if not isinstance(block, dict):
        return RequestLimits()
    limits = _from_mapping(block)
    limits.validate()
    return limits


def _from_mapping(block: dict[str, Any]) -> RequestLimits:
    return RequestLimits(
        max_query_chars=int(
            block.get("max_query_chars", DEFAULT_MAX_QUERY_CHARS)
        )
    )

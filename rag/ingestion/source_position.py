"""
Maps chunk character ranges back to source segments.

This is the generic bridge between extraction provenance and chunk metadata. It
deals only in labels and ordinals, so it works identically for PDF pages, plain
text, and any future format — nothing here knows what a page is.

Offset alignment: segment offsets refer to *extracted* text, while chunking runs
on *normalized* text, and normalization changes string length. Carrying raw
offsets across that boundary would silently mis-attribute citations, so
`normalize_segments` re-derives the spans by normalizing each segment
independently and concatenating the results.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from rag.ingestion.extraction.types import SourceSegment

SEGMENT_JOINER = "\n\n"


@dataclass(frozen=True, slots=True)
class SourcePosition:
    """Which source segments a chunk came from."""

    label: str | None = None
    start_ordinal: int | None = None
    end_ordinal: int | None = None

    @property
    def is_known(self) -> bool:
        return self.start_ordinal is not None


def normalize_segments(
    segments: Sequence[SourceSegment],
    source_text: str,
    normalize: Callable[[str], str],
) -> tuple[str, tuple[SourceSegment, ...]]:
    """
    Normalize each segment separately and rejoin, keeping offsets consistent.

    Returns the normalized document text and segments whose offsets index into
    it. With a single segment covering the whole document this is equivalent to
    normalizing the document as a whole, so the plain-text path is unchanged.
    """
    if not segments:
        return normalize(source_text), ()

    parts: list[str] = []
    rebuilt: list[SourceSegment] = []
    cursor = 0
    for segment in segments:
        piece = normalize(source_text[segment.char_start : segment.char_end])
        if not piece:
            continue
        if parts:
            cursor += len(SEGMENT_JOINER)
            parts.append(SEGMENT_JOINER)
        start = cursor
        parts.append(piece)
        cursor += len(piece)
        rebuilt.append(
            SourceSegment(
                label=segment.label,
                ordinal=segment.ordinal,
                char_start=start,
                char_end=cursor,
            )
        )
    return "".join(parts), tuple(rebuilt)


def resolve_position(
    char_start: int,
    char_end: int,
    segments: Sequence[SourceSegment],
) -> SourcePosition:
    """Find the segment ordinals a `[char_start, char_end)` range overlaps."""
    if not segments:
        return SourcePosition()
    matched = [
        segment for segment in segments if segment.overlaps(char_start, char_end)
    ]
    if not matched:
        # A chunk that falls between segments is attributed to the nearest
        # preceding one rather than losing provenance entirely.
        preceding = [s for s in segments if s.char_start <= char_start]
        if not preceding:
            return SourcePosition()
        nearest = preceding[-1]
        return SourcePosition(
            label=nearest.label,
            start_ordinal=nearest.ordinal,
            end_ordinal=nearest.ordinal,
        )
    return SourcePosition(
        label=matched[0].label,
        start_ordinal=min(segment.ordinal for segment in matched),
        end_ordinal=max(segment.ordinal for segment in matched),
    )

"""
Adaptive semantic chunking.

Sizes chunks by **word tokens** rather than characters, and builds them out of
whole semantic units so a chunk never begins or ends mid-sentence:

- prose paragraphs are decomposed into sentences
- headings, list items, and table rows are atomic units that are never split
- a heading is never emitted alone; it attaches to the content that follows it
- consecutive chunks overlap by a configurable token count for context continuity

The bad case this exists to prevent is a chunk that ends at
"شرایط استفاده از مرخصی سالانه طبق ماده ۵ ..." — a sentence severed mid-clause,
leaving both halves semantically useless.
"""

from __future__ import annotations

from dataclasses import dataclass

from rag.ingestion.chunking.config import ChunkingConfig
from rag.ingestion.types import ChunkDraft
from rag.nlp.sentences import BlockKind, detect_blocks, split_sentences
from rag.nlp.tokenizer import count_tokens


@dataclass(frozen=True, slots=True)
class SemanticUnit:
    """An indivisible piece of text: one sentence, heading, list item, or row."""

    text: str
    char_start: int
    char_end: int
    kind: BlockKind
    token_count: int

    @property
    def is_heading(self) -> bool:
        return self.kind is BlockKind.HEADING

    @property
    def is_atomic(self) -> bool:
        return self.kind is not BlockKind.PARAGRAPH


class SemanticChunker:
    """Token-budgeted, sentence-aware, structure-preserving chunker."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()
        self._config.validate()

    @property
    def name(self) -> str:
        return "semantic"

    @property
    def config(self) -> ChunkingConfig:
        return self._config

    def split(self, text: str) -> list[ChunkDraft]:
        if not text.strip():
            return []

        units = self.build_units(text)
        if not units:
            return []

        groups = self._group(units)
        drafts: list[ChunkDraft] = []
        for index, group in enumerate(groups):
            drafts.append(
                ChunkDraft(
                    chunk_index=index,
                    content="\n".join(unit.text for unit in group).strip(),
                    char_start=group[0].char_start,
                    char_end=group[-1].char_end,
                )
            )
        return [draft for draft in drafts if draft.content]

    def build_units(self, text: str) -> list[SemanticUnit]:
        """Decompose text into indivisible semantic units in document order."""
        units: list[SemanticUnit] = []
        for block in detect_blocks(text):
            if self._config.respect_structure and block.is_structured:
                units.append(self._unit(block.text, block.char_start, block.char_end, block.kind))
                continue
            if not self._config.respect_sentences:
                units.append(
                    self._unit(block.text, block.char_start, block.char_end, block.kind)
                )
                continue
            for sentence in split_sentences(block.text):
                start = block.char_start + sentence.char_start
                units.append(
                    self._unit(
                        sentence.text,
                        start,
                        start + len(sentence.text),
                        BlockKind.PARAGRAPH,
                    )
                )
        return units

    @staticmethod
    def _unit(text: str, start: int, end: int, kind: BlockKind) -> SemanticUnit:
        return SemanticUnit(
            text=text,
            char_start=start,
            char_end=end,
            kind=kind,
            token_count=count_tokens(text),
        )

    def _group(self, units: list[SemanticUnit]) -> list[list[SemanticUnit]]:
        max_tokens = self._config.max_tokens
        groups: list[list[SemanticUnit]] = []
        current: list[SemanticUnit] = []
        current_tokens = 0

        for unit in units:
            # A unit larger than the whole budget cannot be split without
            # breaking a sentence, so it becomes its own chunk.
            if unit.token_count >= max_tokens:
                # Any headings pending at the tail introduce this unit, so they
                # travel with it rather than being stranded as their own chunk.
                carried = self._pop_trailing_headings(current)
                if current:
                    groups.append(current)
                groups.append([*carried, unit])
                current = []
                current_tokens = 0
                continue

            if current and current_tokens + unit.token_count > max_tokens:
                if self._trailing_headings(current):
                    # Never end a chunk on a heading: move it to the next chunk
                    # so it stays with the content it introduces.
                    carried = self._pop_trailing_headings(current)
                    if current:
                        groups.append(current)
                    current = carried
                    current_tokens = sum(item.token_count for item in current)
                else:
                    groups.append(current)
                    current = self._overlap_units(current)
                    current_tokens = sum(item.token_count for item in current)

            current.append(unit)
            current_tokens += unit.token_count

        if current:
            groups.append(current)
        return self._merge_undersized(groups)

    @staticmethod
    def _trailing_headings(units: list[SemanticUnit]) -> bool:
        return bool(units) and units[-1].is_heading

    @staticmethod
    def _pop_trailing_headings(units: list[SemanticUnit]) -> list[SemanticUnit]:
        carried: list[SemanticUnit] = []
        while units and units[-1].is_heading:
            carried.insert(0, units.pop())
        return carried

    def _overlap_units(self, units: list[SemanticUnit]) -> list[SemanticUnit]:
        """
        Contiguous tail of the previous chunk, up to the overlap token budget.

        Scanning stops at the first unit that does not fit so the overlap is
        always a contiguous suffix; skipping over one would splice
        non-adjacent text into the next chunk.
        """
        budget = self._config.overlap_tokens
        if budget <= 0:
            return []
        carried: list[SemanticUnit] = []
        total = 0
        for unit in reversed(units):
            if unit.is_atomic and not unit.is_heading:
                break
            if total + unit.token_count > budget:
                break
            carried.insert(0, unit)
            total += unit.token_count

        if carried:
            return carried

        # A single sentence longer than the overlap budget would otherwise mean
        # no continuity at all. Carry it anyway when it still leaves room for
        # new content, so consecutive chunks always share context.
        last = units[-1]
        if not last.is_atomic and last.token_count < self._config.max_tokens:
            return [last]
        return []

    def _merge_undersized(
        self,
        groups: list[list[SemanticUnit]],
    ) -> list[list[SemanticUnit]]:
        """Fold a too-small trailing chunk back into its predecessor."""
        minimum = self._config.min_chunk_tokens
        if minimum <= 0 or len(groups) < 2:
            return groups
        last = groups[-1]
        last_tokens = sum(unit.token_count for unit in last)
        if last_tokens >= minimum:
            return groups
        previous = groups[-2]
        combined = sum(unit.token_count for unit in previous) + last_tokens
        if combined > self._config.max_tokens:
            return groups
        merged = groups[:-2]
        merged.append(previous + last)
        return merged

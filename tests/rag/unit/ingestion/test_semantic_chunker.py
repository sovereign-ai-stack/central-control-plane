"""
Adaptive semantic chunking tests (Phase 5F).

The headline requirement: chunk boundaries must fall on semantic boundaries, so
a chunk never ends mid-sentence the way character-budget splitting does.
"""

from __future__ import annotations

import pytest

from rag.ingestion.chunker import chunk_text
from rag.ingestion.chunking import (
    STRATEGY_SEMANTIC,
    ChunkingConfig,
    ChunkingStrategy,
    FixedCharChunker,
    SemanticChunker,
    create_chunker,
    load_chunking_config,
)
from rag.ingestion.errors import IngestValidationError
from rag.nlp.sentences import split_sentences
from rag.nlp.tokenizer import count_tokens

PARAGRAPH = (
    "شرایط استفاده از مرخصی سالانه طبق ماده ۵ قانون کار تعیین می‌شود. "
    "کارکنان تمام‌وقت پس از یک سال خدمت مشمول این ماده هستند. "
    "درخواست مرخصی باید حداقل ده روز قبل در سامانه ثبت شود. "
    "مدیر مستقیم موظف است ظرف سه روز کاری پاسخ دهد."
)

STRUCTURED = """ماده ۵ مرخصی سالانه

شرایط استفاده از مرخصی سالانه طبق ماده ۵ قانون کار تعیین می‌شود. کارکنان مشمول هستند.

- مورد اول فهرست مرخصی
- مورد دوم فهرست مرخصی
- مورد سوم فهرست مرخصی

| ستون اول | ستون دوم |

بخش دوم راهنمای داخلی

این پاراگراف پایانی است و شامل دو جمله می‌شود. جمله آخر اینجاست."""


def _chunker(**overrides) -> SemanticChunker:
    config = ChunkingConfig(
        strategy=STRATEGY_SEMANTIC,
        max_tokens=overrides.pop("max_tokens", 25),
        overlap_tokens=overrides.pop("overlap_tokens", 0),
        min_chunk_tokens=overrides.pop("min_chunk_tokens", 0),
        **overrides,
    )
    return SemanticChunker(config)


class TestBoundaryCorrectness:
    def test_no_chunk_ends_mid_sentence(self):
        chunks = _chunker(max_tokens=20).split(PARAGRAPH)
        assert len(chunks) > 1
        source_sentences = {s.text for s in split_sentences(PARAGRAPH)}
        for chunk in chunks:
            for line in chunk.content.split("\n"):
                assert line.strip() in source_sentences

    def test_sentences_are_never_severed(self):
        chunks = _chunker(max_tokens=20).split(PARAGRAPH)
        rebuilt = " ".join(chunk.content.replace("\n", " ") for chunk in chunks)
        for sentence in split_sentences(PARAGRAPH):
            assert sentence.text in rebuilt

    def test_the_bad_case_from_the_brief_does_not_occur(self):
        # "شرایط استفاده از مرخصی سالانه طبق ماده ۵ ..." must not be cut mid-clause.
        chunks = _chunker(max_tokens=12).split(PARAGRAPH)
        opening = "شرایط استفاده از مرخصی سالانه طبق ماده ۵ قانون کار تعیین می‌شود."
        assert any(opening in chunk.content for chunk in chunks)

    def test_oversized_sentence_becomes_its_own_chunk(self):
        long_sentence = " ".join(f"کلمه{i}" for i in range(60)) + "."
        chunks = _chunker(max_tokens=10).split(long_sentence)
        assert len(chunks) == 1
        assert chunks[0].content.endswith(".")

    def test_chunk_indices_are_sequential(self):
        chunks = _chunker(max_tokens=15).split(STRUCTURED)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_char_offsets_are_ordered_and_non_negative(self):
        chunks = _chunker(max_tokens=15).split(STRUCTURED)
        for chunk in chunks:
            assert 0 <= chunk.char_start <= chunk.char_end
        starts = [c.char_start for c in chunks]
        assert starts == sorted(starts)


class TestStructurePreservation:
    def test_list_items_are_never_split(self):
        chunks = _chunker(max_tokens=8).split(STRUCTURED)
        joined = "\n".join(chunk.content for chunk in chunks)
        for item in ("- مورد اول فهرست مرخصی", "- مورد دوم فهرست مرخصی"):
            assert item in joined

    def test_table_row_kept_intact(self):
        chunks = _chunker(max_tokens=8).split(STRUCTURED)
        joined = "\n".join(chunk.content for chunk in chunks)
        assert "| ستون اول | ستون دوم |" in joined

    def test_heading_never_ends_a_chunk_alone(self):
        chunks = _chunker(max_tokens=10).split(STRUCTURED)
        for chunk in chunks:
            lines = [line for line in chunk.content.split("\n") if line.strip()]
            if len(lines) == 1 and lines[0].startswith("ماده"):
                pytest.fail("heading was emitted as a standalone chunk")

    def test_heading_stays_with_following_content(self):
        chunks = _chunker(max_tokens=14).split(STRUCTURED)
        for chunk in chunks:
            lines = [line for line in chunk.content.split("\n") if line.strip()]
            if lines and lines[0].startswith("ماده ۵"):
                assert len(lines) > 1
                return
        pytest.fail("heading chunk not found")

    def test_structure_awareness_can_be_disabled(self):
        config = ChunkingConfig(
            strategy=STRATEGY_SEMANTIC,
            max_tokens=25,
            overlap_tokens=0,
            respect_structure=False,
        )
        assert SemanticChunker(config).split(STRUCTURED)


class TestTokenBudget:
    def test_chunks_respect_the_token_budget(self):
        budget = 25
        chunks = _chunker(max_tokens=budget).split(PARAGRAPH)
        for chunk in chunks:
            # Only a single oversized semantic unit may exceed the budget.
            lines = [line for line in chunk.content.split("\n") if line.strip()]
            if len(lines) > 1:
                assert count_tokens(chunk.content) <= budget

    def test_smaller_budget_produces_more_chunks(self):
        few = _chunker(max_tokens=60).split(PARAGRAPH)
        many = _chunker(max_tokens=12).split(PARAGRAPH)
        assert len(many) > len(few)

    def test_short_text_yields_one_chunk(self):
        chunks = _chunker(max_tokens=100).split("یک جمله کوتاه.")
        assert len(chunks) == 1

    def test_empty_text_yields_no_chunks(self):
        assert _chunker().split("   ") == []


class TestOverlap:
    def test_overlap_repeats_trailing_context(self):
        chunks = _chunker(max_tokens=20, overlap_tokens=8).split(PARAGRAPH)
        assert len(chunks) > 1
        first_lines = set(chunks[0].content.split("\n"))
        second_lines = set(chunks[1].content.split("\n"))
        assert first_lines & second_lines

    def test_zero_overlap_produces_disjoint_chunks(self):
        chunks = _chunker(max_tokens=20, overlap_tokens=0).split(PARAGRAPH)
        seen: set[str] = set()
        for chunk in chunks:
            for line in chunk.content.split("\n"):
                assert line not in seen
                seen.add(line)

    def test_overlap_still_terminates(self):
        chunks = _chunker(max_tokens=20, overlap_tokens=19).split(PARAGRAPH * 3)
        assert 0 < len(chunks) < 200


class TestMinChunkSize:
    def test_small_trailing_chunk_is_merged(self):
        text = PARAGRAPH + " پایان."
        without = _chunker(max_tokens=30, min_chunk_tokens=0).split(text)
        with_minimum = _chunker(max_tokens=30, min_chunk_tokens=20).split(text)
        assert len(with_minimum) <= len(without)


class TestStrategySelection:
    def test_default_strategy_is_fixed_char(self):
        assert ChunkingConfig().strategy == "fixed_char"
        assert isinstance(create_chunker(), FixedCharChunker)

    def test_shipped_config_keeps_legacy_default(self):
        assert load_chunking_config().strategy == "fixed_char"

    def test_fixed_char_matches_legacy_function(self):
        text = "پاراگراف اول.\n\n" + ("جمله تست. " * 50)
        config = ChunkingConfig(max_chars=200)
        assert FixedCharChunker(config).split(text) == chunk_text(text, max_chars=200)

    def test_semantic_strategy_selected_by_config(self):
        chunker = create_chunker(
            ChunkingConfig(strategy=STRATEGY_SEMANTIC, max_tokens=50, overlap_tokens=5)
        )
        assert isinstance(chunker, SemanticChunker)

    def test_both_strategies_satisfy_the_protocol(self):
        assert isinstance(FixedCharChunker(), ChunkingStrategy)
        assert isinstance(SemanticChunker(ChunkingConfig(strategy="semantic")), ChunkingStrategy)

    def test_deterministic_output(self):
        chunker = _chunker(max_tokens=20, overlap_tokens=5)
        assert chunker.split(STRUCTURED) == chunker.split(STRUCTURED)


class TestConfigValidation:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"strategy": "magic"},
            {"max_tokens": 0},
            {"max_tokens": 999_999},
            {"overlap_tokens": -1},
            {"overlap_tokens": 500, "max_tokens": 100},
            {"max_chars": 0},
        ],
    )
    def test_invalid_configuration_rejected(self, overrides):
        config = ChunkingConfig(**overrides)
        with pytest.raises(IngestValidationError):
            config.validate()

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        assert load_chunking_config(tmp_path / "absent.yaml") == ChunkingConfig()

    def test_config_file_is_loaded(self, tmp_path):
        path = tmp_path / "chunking.yaml"
        path.write_text(
            "chunking:\n  strategy: semantic\n  max_tokens: 120\n  overlap_tokens: 10\n",
            encoding="utf-8",
        )
        config = load_chunking_config(path)
        assert config.strategy == "semantic"
        assert config.max_tokens == 120

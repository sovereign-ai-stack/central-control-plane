"""
Morphological normalization tests (Phase 5C).

Covers the cases named in the phase brief plus the over-stemming guards, since
aggressive Persian light stemming can cost more recall than it gains.
"""

from __future__ import annotations

import pytest

from rag.nlp.morphology import (
    PROTECTED_WORDS,
    MorphologyRules,
    lemmatize_token,
    lemmatize_tokens,
)
from rag.nlp.normalizer import ZWNJ


class TestPluralForms:
    @pytest.mark.parametrize(
        "surface",
        [f"کتاب{ZWNJ}ها", "کتابها", "کتابهای", f"کتاب{ZWNJ}های", "کتابهایی", "کتاب"],
    )
    def test_book_inflections_collapse_to_one_root(self, surface):
        assert lemmatize_token(surface) == "کتاب"

    def test_zwnj_and_joined_plurals_agree(self):
        assert lemmatize_token(f"کتاب{ZWNJ}ها") == lemmatize_token("کتابها")

    def test_arabic_style_plural_suffix(self):
        assert lemmatize_token("کارکنان") == "کارکن"

    def test_plural_rule_can_be_disabled(self):
        rules = MorphologyRules(plural=False, verbs=False)
        assert lemmatize_token("کتابها", rules) == "کتابها"


class TestVerbForms:
    @pytest.mark.parametrize("surface", [f"می{ZWNJ}روم", "میروم", f"می{ZWNJ}رود", "میرویم"])
    def test_present_verb_maps_to_infinitive(self, surface):
        assert lemmatize_token(surface) == "رفتن"

    def test_negated_verb_maps_to_infinitive(self):
        assert lemmatize_token(f"نمی{ZWNJ}رود") == "رفتن"

    def test_zwnj_and_joined_verb_spellings_agree(self):
        assert lemmatize_token(f"می{ZWNJ}روم") == lemmatize_token("میروم")

    @pytest.mark.parametrize(
        ("surface", "expected"),
        [
            (f"می{ZWNJ}کند", "کردن"),
            (f"می{ZWNJ}گوید", "گفتن"),
            (f"می{ZWNJ}دهد", "دادن"),
        ],
    )
    def test_common_irregular_verbs(self, surface, expected):
        assert lemmatize_token(surface) == expected

    def test_verb_rule_can_be_disabled(self):
        rules = MorphologyRules(verbs=False)
        assert lemmatize_token("میروم", rules) != "رفتن"


class TestComparativeAndPossessive:
    def test_comparative_stripped(self):
        assert lemmatize_token("بزرگتر") == "بزرگ"
        assert lemmatize_token("بزرگترین") == "بزرگ"

    def test_possessive_stripped(self):
        assert lemmatize_token("کتابمان") == "کتاب"

    def test_comparative_rule_can_be_disabled(self):
        rules = MorphologyRules(comparative=False, verbs=False, plural=False)
        assert lemmatize_token("بزرگتر", rules) == "بزرگتر"


class TestOverStemmingGuards:
    @pytest.mark.parametrize(
        "word", ["تهران", "زبان", "جهان", "انسان", "سازمان", "خانه", "ماده", "سالانه"]
    )
    def test_protected_words_untouched(self, word):
        assert lemmatize_token(word) == word

    def test_protected_list_is_respected_by_the_rules(self):
        for word in list(PROTECTED_WORDS)[:20]:
            assert lemmatize_token(word) == word

    def test_short_tokens_never_stemmed(self):
        for word in ["ها", "من", "او", "به", "را"]:
            assert lemmatize_token(word) == word

    def test_min_stem_length_blocks_aggressive_stripping(self):
        strict = MorphologyRules(min_stem_length=10)
        assert lemmatize_token("کتابها", strict) == "کتابها"

    def test_stem_never_shrinks_below_min_length(self):
        rules = MorphologyRules()
        for surface in ["کتابها", "بزرگترین", "کارکنان", "کتابهایی"]:
            assert len(lemmatize_token(surface, rules)) >= rules.min_stem_length


class TestDeterminismAndIdempotency:
    @pytest.mark.parametrize(
        "surface",
        [f"کتاب{ZWNJ}ها", "کتابهای", f"می{ZWNJ}روم", "بزرگترین", "تهران", "کتاب", ""],
    )
    def test_lemmatizing_twice_changes_nothing(self, surface):
        once = lemmatize_token(surface)
        assert lemmatize_token(once) == once

    def test_same_input_same_output(self):
        assert lemmatize_token("کتابها") == lemmatize_token("کتابها")

    def test_batch_preserves_order_and_length(self):
        tokens = ["کتابها", "تهران", f"می{ZWNJ}روم", "مرخصی"]
        lemmas = lemmatize_tokens(tokens)
        assert len(lemmas) == len(tokens)
        assert lemmas[0] == "کتاب"
        assert lemmas[1] == "تهران"

    def test_empty_token(self):
        assert lemmatize_token("") == ""

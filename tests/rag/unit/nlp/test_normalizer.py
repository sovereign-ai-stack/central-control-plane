"""
fa-norm-v2 normalization tests (Phase 5C).

Includes a regression guard pinning fa-norm-v1 output, because v1 feeds stored
content hashes, chunk dedup keys, the retrieval lexical scorer, and the Phase 4
query hash. v2 must be purely additive.
"""

from __future__ import annotations

import pytest

from rag.ingestion.persian import normalization_version, normalize_persian
from rag.nlp.normalizer import (
    NORMALIZATION_VERSION_V2,
    ZWNJ,
    normalize_persian_v2,
    strip_zwnj,
)

ARABIC_YEH = "ي"
PERSIAN_YEH = "ی"
ARABIC_KAF = "ك"
PERSIAN_KAF = "ک"


class TestCharacterNormalization:
    def test_arabic_yeh_to_persian_yeh(self):
        assert normalize_persian_v2(f"عل{ARABIC_YEH}") == f"عل{PERSIAN_YEH}"
        assert ARABIC_YEH not in normalize_persian_v2("مرخصي سالانه")

    def test_arabic_kaf_to_persian_kaf(self):
        assert normalize_persian_v2(f"{ARABIC_KAF}تاب") == f"{PERSIAN_KAF}تاب"
        assert ARABIC_KAF not in normalize_persian_v2("كارمند")

    def test_arabic_variant_spelling_matches_persian(self):
        assert normalize_persian_v2("مرخصي سالانه") == normalize_persian_v2("مرخصی سالانه")

    def test_alef_maksura_and_hamza_forms(self):
        assert normalize_persian_v2("علی") == normalize_persian_v2("على")
        assert normalize_persian_v2("مسئله") == normalize_persian_v2("مسیله")

    def test_teh_marbuta_to_heh(self):
        assert normalize_persian_v2("مرحلة") == "مرحله"

    def test_tatweel_removed(self):
        assert normalize_persian_v2("مـــرخصی") == "مرخصی"

    def test_diacritics_removed(self):
        assert normalize_persian_v2("مُرَخَّصی") == "مرخصی"

    def test_punctuation_normalized(self):
        assert normalize_persian_v2("«نقل قول»") == '"نقل قول"'
        assert normalize_persian_v2("یک — دو") == "یک - دو"

    def test_digits_preserved_by_default(self):
        assert normalize_persian_v2("۲۶ روز") == "۲۶ روز"

    def test_digits_folded_when_requested(self):
        assert normalize_persian_v2("۲۶ روز", fold_digits=True) == "26 روز"
        assert normalize_persian_v2("٤٥ يوم", fold_digits=True).startswith("45")


class TestZwnjHandling:
    def test_zwnj_preserved_between_letters(self):
        # The whole point of v2: keep the compound joinable for morphology.
        assert normalize_persian_v2(f"کتاب{ZWNJ}ها") == f"کتاب{ZWNJ}ها"

    def test_repeated_zwnj_collapsed(self):
        assert normalize_persian_v2(f"کتاب{ZWNJ}{ZWNJ}{ZWNJ}ها") == f"کتاب{ZWNJ}ها"

    def test_zwnj_surrounded_by_spaces_becomes_space(self):
        assert normalize_persian_v2(f"کتاب  {ZWNJ}  ها") == "کتاب ها"

    def test_zwnj_at_edges_removed(self):
        assert normalize_persian_v2(f"{ZWNJ}کتاب{ZWNJ}") == "کتاب"

    def test_zero_width_joiner_removed(self):
        assert normalize_persian_v2("کتاب‍ها") == "کتابها"

    def test_strip_zwnj_helper_unifies_spellings(self):
        assert strip_zwnj(normalize_persian_v2(f"می{ZWNJ}روم")) == normalize_persian_v2(
            "میروم"
        )


class TestWhitespace:
    def test_spaces_collapsed(self):
        assert normalize_persian_v2("سلام   دنیا") == "سلام دنیا"

    def test_line_endings_normalized(self):
        assert normalize_persian_v2("خط\r\nدوم") == "خط\nدوم"

    def test_excess_blank_lines_collapsed(self):
        assert normalize_persian_v2("الف\n\n\n\n\nب") == "الف\n\nب"

    def test_leading_and_trailing_trimmed(self):
        assert normalize_persian_v2("  متن  ") == "متن"

    def test_empty_input(self):
        assert normalize_persian_v2("") == ""


class TestIdempotency:
    @pytest.mark.parametrize(
        "text",
        [
            "کتاب‌ها",
            "مرخصي   سالانه",
            "مُرَخَّصی",
            "«نقل قول»",
            f"{ZWNJ}کتاب{ZWNJ}{ZWNJ}ها{ZWNJ}",
            "خط\r\n\r\n\r\nدوم",
            "۲۶ روز",
            "",
        ],
    )
    def test_normalizing_twice_changes_nothing(self, text):
        once = normalize_persian_v2(text)
        assert normalize_persian_v2(once) == once

    def test_version_identifier(self):
        assert NORMALIZATION_VERSION_V2 == "fa-norm-v2"


class TestV1Regression:
    """fa-norm-v1 must not shift: persisted hashes and dedup keys depend on it."""

    def test_v1_version_unchanged(self):
        assert normalization_version() == "fa-norm-v1"

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("علي", "علی"),
            ("كتاب", "کتاب"),
            ("سلام   دنیا", "سلام دنیا"),
            (f"مرخصی{ZWNJ}سالانه", "مرخصی سالانه"),
            ("  متن  ", "متن"),
            ("خط\r\nدوم", "خط\nدوم"),
        ],
    )
    def test_v1_output_pinned(self, text, expected):
        assert normalize_persian(text) == expected

    def test_v1_still_maps_zwnj_to_space(self):
        assert normalize_persian(f"کتاب{ZWNJ}ها") == "کتاب ها"

    def test_v2_differs_from_v1_only_where_intended(self):
        # Same result for the plain cases, different only on ZWNJ handling.
        assert normalize_persian("علي كتاب") == normalize_persian_v2("علي كتاب")
        assert normalize_persian(f"کتاب{ZWNJ}ها") != normalize_persian_v2(f"کتاب{ZWNJ}ها")

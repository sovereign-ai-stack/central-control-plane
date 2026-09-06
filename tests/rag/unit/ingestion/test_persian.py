"""Persian normalization unit tests."""

from __future__ import annotations

from rag.ingestion.persian import normalization_version, normalize_persian


class TestPersianNormalization:
    def test_arabic_yeh_mapped(self):
        assert normalize_persian("علي") == "علی"

    def test_arabic_kaf_mapped(self):
        assert normalize_persian("كتاب") == "کتاب"

    def test_whitespace_collapsed(self):
        assert normalize_persian("سلام   دنیا") == "سلام دنیا"

    def test_zwnj_normalized_to_space(self):
        assert normalize_persian("مرخصی\u200cسالانه") == "مرخصی سالانه"

    def test_normalization_version(self):
        assert normalization_version() == "fa-norm-v1"

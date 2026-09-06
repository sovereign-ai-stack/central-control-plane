"""
Tokenizer, sentence segmentation, and PersianNlpPipeline tests (Phase 5C/5D).
"""

from __future__ import annotations

import pytest

from rag.nlp.backends import RuleBasedMorphologyBackend, create_backend, hazm_available
from rag.nlp.backends.protocol import MorphologyBackend
from rag.nlp.config import MorphologyConfig, NlpConfig, load_nlp_config
from rag.nlp.errors import NlpBackendUnavailableError, NlpConfigurationError
from rag.nlp.normalizer import ZWNJ
from rag.nlp.pipeline import PersianNlpPipeline
from rag.nlp.sentences import BlockKind, classify_line, detect_blocks, split_sentences
from rag.nlp.tokenizer import count_tokens, tokenize, tokenize_with_spans


def _pipeline(*, morphology: bool = False) -> PersianNlpPipeline:
    return PersianNlpPipeline(
        NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=morphology))
    )


class TestTokenizer:
    def test_splits_on_whitespace_and_punctuation(self):
        assert tokenize("مرخصی سالانه، کارکنان.") == ["مرخصی", "سالانه", "کارکنان"]

    def test_zwnj_compound_is_one_token(self):
        assert tokenize(f"کتاب{ZWNJ}ها") == [f"کتاب{ZWNJ}ها"]

    def test_spaced_compound_is_two_tokens(self):
        assert len(tokenize("کتاب ها")) == 2

    def test_latin_and_digits_tokenized(self):
        assert tokenize("VPN port 8080") == ["VPN", "port", "8080"]

    def test_spans_map_back_to_source(self):
        text = "مرخصی سالانه"
        for surface, start, end in tokenize_with_spans(text):
            assert text[start:end] == surface

    def test_count_tokens(self):
        assert count_tokens("یک دو سه") == 3
        assert count_tokens("") == 0


class TestSentenceSegmentation:
    def test_splits_on_persian_question_mark(self):
        sentences = split_sentences("مرخصی چند روز است؟ بیست و شش روز.")
        assert len(sentences) == 2

    def test_terminator_stays_attached(self):
        sentences = split_sentences("جمله اول. جمله دوم.")
        assert sentences[0].text.endswith(".")

    def test_offsets_map_back_to_source(self):
        text = "جمله اول. جمله دوم؟"
        for sentence in split_sentences(text):
            assert text[sentence.char_start : sentence.char_end] == sentence.text

    def test_newline_terminates_a_sentence(self):
        sentences = split_sentences("عنوان بخش\nمتن بعدی.")
        assert len(sentences) == 2

    def test_abbreviation_does_not_split(self):
        sentences = split_sentences("مطابق ص. ۱۲ قانون کار عمل شود.")
        assert len(sentences) == 1

    def test_decimal_number_does_not_split(self):
        sentences = split_sentences("مبلغ 3.5 میلیون ریال است.")
        assert len(sentences) == 1

    def test_empty_text(self):
        assert split_sentences("") == []

    def test_deterministic(self):
        text = "الف. ب؟ ج!"
        assert split_sentences(text) == split_sentences(text)


class TestBlockDetection:
    @pytest.mark.parametrize(
        ("line", "kind"),
        [
            ("ماده ۵ قانون کار", BlockKind.HEADING),
            ("## عنوان", BlockKind.HEADING),
            ("۲.۳ زیربخش", BlockKind.HEADING),
            ("- مورد اول", BlockKind.LIST_ITEM),
            ("۱. مورد اول", BlockKind.LIST_ITEM),
            ("• مورد", BlockKind.LIST_ITEM),
            ("| ستون | مقدار |", BlockKind.TABLE_ROW),
            ("این یک پاراگراف عادی است.", BlockKind.PARAGRAPH),
        ],
    )
    def test_line_classification(self, line, kind):
        assert classify_line(line) == kind

    def test_consecutive_prose_lines_merge_into_one_paragraph(self):
        blocks = detect_blocks("خط اول ادامه\nخط دوم ادامه")
        assert len(blocks) == 1
        assert blocks[0].kind is BlockKind.PARAGRAPH

    def test_structured_lines_stay_separate(self):
        blocks = detect_blocks("ماده ۵ قانون کار\n- مورد اول\n- مورد دوم")
        assert [b.kind for b in blocks] == [
            BlockKind.HEADING,
            BlockKind.LIST_ITEM,
            BlockKind.LIST_ITEM,
        ]
        assert all(block.is_structured for block in blocks)

    def test_block_offsets_map_back_to_source(self):
        text = "ماده ۵\nمتن پاراگراف اینجاست"
        for block in detect_blocks(text):
            assert block.text in text[block.char_start : block.char_end + 1]


class TestPipelineDisabledByDefault:
    def test_default_config_is_off(self):
        config = NlpConfig()
        assert config.enabled is False
        assert config.morphology.enabled is False

    def test_shipped_config_file_is_off(self):
        config = load_nlp_config()
        assert config.enabled is False
        assert config.morphology.enabled is False

    def test_morphology_off_leaves_embedding_text_as_normalized(self):
        pipeline = _pipeline(morphology=False)
        result = pipeline.process(f"کتاب{ZWNJ}های مرخصی")
        assert result.embedding_text == result.normalized
        assert result.morphology_applied is False


class TestPipelineProcessing:
    def test_keeps_original_normalized_and_embedding_representations(self):
        pipeline = _pipeline(morphology=True)
        raw = "  كتابهاي   مرخصي  "
        result = pipeline.process(raw)
        assert result.original == raw
        assert result.normalized == "کتابهای مرخصی"
        assert result.embedding_text != result.normalized
        assert result.original != result.normalized

    def test_morphology_reduces_inflections(self):
        pipeline = _pipeline(morphology=True)
        assert pipeline.embedding_text("کتابها") == pipeline.embedding_text(
            f"کتاب{ZWNJ}های"
        )

    def test_punctuation_and_spacing_preserved_when_splicing_lemmas(self):
        pipeline = _pipeline(morphology=True)
        result = pipeline.process("کتابها، مرخصی. پایان!")
        assert "،" in result.embedding_text
        assert result.embedding_text.endswith("!")

    def test_query_and_document_use_the_same_transform(self):
        pipeline = _pipeline(morphology=True)
        text = f"کتاب{ZWNJ}های مرخصی سالانه"
        assert (
            pipeline.process_query(text).embedding_text
            == pipeline.process_document(text).embedding_text
        )

    @pytest.mark.parametrize("morphology", [False, True])
    def test_processing_is_idempotent(self, morphology):
        pipeline = _pipeline(morphology=morphology)
        text = f"  كتاب{ZWNJ}هاي   مرخصي سالانه. می{ZWNJ}روم؟  "
        once = pipeline.process(text).embedding_text
        assert pipeline.process(once).embedding_text == once

    def test_tokens_and_sentences_exposed(self):
        pipeline = _pipeline(morphology=True)
        result = pipeline.process("مرخصی سالانه. کارکنان می‌روند؟")
        assert result.token_count > 0
        assert result.sentence_count == 2
        assert all(token.lemma for token in result.tokens)

    def test_version_records_morphology_state(self):
        assert "nomorph" in _pipeline(morphology=False).version
        assert "morph" in _pipeline(morphology=True).version
        assert "fa-norm-v2" in _pipeline().version

    def test_empty_text(self):
        result = _pipeline(morphology=True).process("")
        assert result.normalized == ""
        assert result.embedding_text == ""
        assert result.token_count == 0


class TestBackends:
    def test_rule_based_is_the_default(self):
        backend = create_backend("rule_based")
        assert isinstance(backend, RuleBasedMorphologyBackend)
        assert isinstance(backend, MorphologyBackend)
        assert backend.name == "rule_based"

    def test_backend_preserves_token_count(self):
        backend = create_backend("rule_based")
        tokens = ["کتابها", "تهران", "مرخصی"]
        assert len(backend.lemmatize(tokens)) == len(tokens)

    def test_unknown_backend_rejected(self):
        with pytest.raises(NlpConfigurationError):
            create_backend("word2vec")

    def test_hazm_backend_reports_unavailability_clearly(self):
        # hazm is an optional extra and is not installable on this interpreter
        # (it requires gensim, which has no wheel here), so the factory must
        # raise a typed error rather than an ImportError.
        if hazm_available():
            pytest.skip("hazm is installed in this environment")
        with pytest.raises(NlpBackendUnavailableError):
            create_backend("hazm")

    def test_pipeline_accepts_an_injected_backend(self):
        class UpperBackend:
            name = "upper"

            def lemmatize(self, tokens: list[str]) -> list[str]:
                return [token.upper() for token in tokens]

        pipeline = PersianNlpPipeline(
            NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=True)),
            backend=UpperBackend(),
        )
        assert pipeline.process("abc def").embedding_text == "ABC DEF"


class TestConfiguration:
    def test_rejects_unsupported_normalization_version(self, tmp_path):
        path = tmp_path / "nlp.yaml"
        path.write_text("nlp:\n  normalization_version: fa-norm-v1\n", encoding="utf-8")
        with pytest.raises(NlpConfigurationError):
            load_nlp_config(path)

    def test_rejects_invalid_min_stem_length(self, tmp_path):
        path = tmp_path / "nlp.yaml"
        path.write_text(
            "nlp:\n  morphology:\n    min_stem_length: 0\n", encoding="utf-8"
        )
        with pytest.raises(NlpConfigurationError):
            load_nlp_config(path)

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        assert load_nlp_config(tmp_path / "absent.yaml") == NlpConfig()

    def test_per_rule_toggles_load(self, tmp_path):
        path = tmp_path / "nlp.yaml"
        path.write_text(
            "nlp:\n  enabled: true\n  morphology:\n    enabled: true\n    verbs: false\n",
            encoding="utf-8",
        )
        config = load_nlp_config(path)
        assert config.enabled is True
        assert config.morphology.verbs is False
        assert config.morphology.plural is True

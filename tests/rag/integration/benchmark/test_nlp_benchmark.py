"""
Tests for the Phase 5 benchmark additions (5G/5H).

Covers the fa-retrieval-v2 dataset, the NLP A/B comparison, and the chunk-level
harness. These assert *mechanics and integrity*, not quality: scores here come
from the deterministic stub model and are not a retrieval-quality signal.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from benchmarks.persian.chunk_benchmark import (
    ChunkShapeStats,
    compare_strategies,
    evaluate_chunking,
)
from benchmarks.persian.compare_nlp import (
    MODES,
    build_comparison,
    evaluate_mode,
    nlp_config_for,
    render_markdown,
    run_comparison,
)
from benchmarks.persian.dataset import load_dataset, query_category
from benchmarks.persian.generate_dataset import generate_dataset
from benchmarks.persian.validate_dataset import validate_dataset

from rag.ingestion.chunking import ChunkingConfig
from rag.nlp.config import MorphologyConfig, NlpConfig

REPO_ROOT = Path(__file__).resolve().parents[4]
V1_DIR = REPO_ROOT / "benchmarks" / "persian" / "data" / "fa-retrieval-v1"
V2_DIR = REPO_ROOT / "benchmarks" / "persian" / "data" / "fa-retrieval-v2"
CANDIDATES = REPO_ROOT / "benchmarks" / "persian" / "config" / "candidates.yaml"

MORPHOLOGY_CATEGORIES = {
    "morphology",
    "plural_forms",
    "verb_forms",
    "spelling_variants",
}


@pytest.fixture(scope="module", autouse=True)
def ensure_datasets() -> None:
    generate_dataset(V1_DIR, dataset_version="fa-retrieval-v1")
    generate_dataset(V2_DIR, dataset_version="fa-retrieval-v2")


class TestDatasetV2:
    def test_v2_validates(self):
        assert validate_dataset(V2_DIR) == []

    def test_v1_still_validates_and_is_unchanged(self):
        # v1 is frozen so earlier benchmark runs stay comparable.
        assert validate_dataset(V1_DIR) == []
        assert load_dataset(V1_DIR).dataset_version == "fa-retrieval-v1"

    def test_v1_has_no_morphology_categories(self):
        categories = {q.category for q in load_dataset(V1_DIR).queries}
        assert not (categories & MORPHOLOGY_CATEGORIES)

    def test_v2_adds_every_morphology_category(self):
        categories = {q.category for q in load_dataset(V2_DIR).queries}
        assert MORPHOLOGY_CATEGORIES <= categories

    def test_v2_morphology_queries_are_document_grounded(self):
        dataset = load_dataset(V2_DIR)
        corpus = {doc.doc_id: doc.text for doc in dataset.corpus}
        checked = 0
        for query in dataset.queries:
            if query.category not in {"morphology", "plural_forms", "verb_forms"}:
                continue
            assert query.relevant_doc_ids[0] in corpus
            checked += 1
        assert checked > 0

    def test_v2_query_categories_resolve(self):
        for query in load_dataset(V2_DIR).queries:
            assert query_category(query)

    def test_v2_contains_long_form_documents_for_chunking(self):
        # Single-sentence documents cannot exercise chunking at all.
        long_docs = [doc for doc in load_dataset(V2_DIR).corpus if len(doc.text) > 200]
        assert len(long_docs) >= 10
        assert any("\n" in doc.text for doc in long_docs)

    def test_checksums_regenerate(self):
        checksums = (V2_DIR / "checksums.sha256").read_text(encoding="utf-8")
        for name in ("corpus.jsonl", "queries.jsonl", "splits.json", "schema.json"):
            assert name in checksums


class TestNlpModeConfiguration:
    def test_off_mode_is_the_pre_phase5_baseline(self):
        assert nlp_config_for("off") is None

    def test_on_mode_enables_normalization_only(self):
        config = nlp_config_for("on")
        assert config.enabled is True
        assert config.morphology.enabled is False

    def test_morphology_mode_enables_both(self):
        config = nlp_config_for("morphology")
        assert config.enabled is True
        assert config.morphology.enabled is True

    def test_unknown_mode_rejected(self):
        with pytest.raises(ValueError, match="unknown mode"):
            nlp_config_for("turbo")

    def test_all_modes_are_configurable(self):
        for mode in MODES:
            nlp_config_for(mode)


@pytest.fixture(scope="module")
def results():
    dataset = load_dataset(V2_DIR)
    return [
        evaluate_mode(
            mode,
            dataset,
            candidate_id="stub",
            candidates_path=CANDIDATES,
            device="cpu",
            split="val",
        )
        for mode in MODES
    ]


@pytest.fixture(scope="module")
def dataset():
    return load_dataset(V2_DIR)


class TestNlpComparison:
    def test_every_mode_produces_metrics(self, results):
        assert len(results) == len(MODES)
        for result in results:
            assert result.aggregate.recall_at_k
            assert result.aggregate.by_category

    def test_modes_record_their_normalization_version(self, results):
        by_mode = {result.mode: result for result in results}
        assert by_mode["off"].normalization_version == "fa-norm-v1"
        assert by_mode["on"].normalization_version == "fa-norm-v2"
        assert by_mode["morphology"].morphology_enabled is True

    def test_comparison_reports_deltas_against_off(self, results):
        comparison = build_comparison(results)
        assert comparison["baseline_mode"] == "off"
        assert comparison["modes"]["off"]["delta_vs_off"]["recall_at_5"] == 0.0
        for mode in MODES:
            assert set(comparison["modes"][mode]["metrics"]) == {
                "recall_at_5",
                "mrr",
                "ndcg_at_5",
                "ndcg_at_10",
            }

    def test_comparison_includes_per_category_deltas(self, results):
        comparison = build_comparison(results)
        categories = comparison["modes"]["morphology"]["by_category"]
        assert MORPHOLOGY_CATEGORIES <= set(categories)
        for values in categories.values():
            assert "delta_recall_at_5" in values

    def test_markdown_report_renders(self, results):
        markdown = render_markdown(build_comparison(results), "stub")
        assert "Recall@5" in markdown
        assert "morphology" in markdown
        assert "| off |" in markdown

    def test_run_comparison_writes_both_artifacts(self, tmp_path):
        run_comparison(
            dataset_dir=V2_DIR,
            candidates_path=CANDIDATES,
            output_dir=tmp_path,
            candidate_id="stub",
            modes=("off", "morphology"),
        )
        assert (tmp_path / "nlp-comparison.json").exists()
        assert (tmp_path / "nlp-comparison.md").exists()

    def test_comparison_is_deterministic(self):
        dataset = load_dataset(V2_DIR)
        runs = [
            evaluate_mode(
                "morphology",
                dataset,
                candidate_id="stub",
                candidates_path=CANDIDATES,
                device="cpu",
                split="val",
            ).aggregate.mrr
            for _ in range(2)
        ]
        assert runs[0] == runs[1]


class TestChunkLevelHarness:
    def test_fixed_char_run_produces_shape_and_metrics(self, dataset):
        result = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(strategy="fixed_char"),
            nlp_config=None,
        )
        assert result["strategy"] == "fixed_char"
        assert result["chunk_shape"]["total_chunks"] > 0
        assert result["chunk_shape"]["empty_chunks"] == 0
        assert 0.0 <= result["metrics"]["recall_at_5"] <= 1.0

    def test_semantic_chunking_never_severs_sentences(self, dataset):
        result = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(
                strategy="semantic", max_tokens=120, overlap_tokens=20
            ),
            nlp_config=None,
        )
        # This is the property the document-level benchmark cannot observe.
        assert result["chunk_shape"]["sentence_boundary_rate"] == 1.0

    def test_semantic_beats_fixed_char_on_boundary_quality(self, dataset):
        fixed = evaluate_chunking(
            dataset, chunking=ChunkingConfig(strategy="fixed_char"), nlp_config=None
        )
        semantic = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(
                strategy="semantic", max_tokens=120, overlap_tokens=20
            ),
            nlp_config=None,
        )
        assert (
            semantic["chunk_shape"]["sentence_boundary_rate"]
            >= fixed["chunk_shape"]["sentence_boundary_rate"]
        )

    def test_smaller_budget_produces_more_chunks(self, dataset):
        coarse = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(strategy="semantic", max_tokens=200, overlap_tokens=0),
            nlp_config=None,
        )
        fine = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(strategy="semantic", max_tokens=20, overlap_tokens=0),
            nlp_config=None,
        )
        assert (
            fine["chunk_shape"]["total_chunks"] > coarse["chunk_shape"]["total_chunks"]
        )

    def test_nlp_flag_is_recorded(self, dataset):
        result = evaluate_chunking(
            dataset,
            chunking=ChunkingConfig(strategy="semantic", max_tokens=120, overlap_tokens=20),
            nlp_config=NlpConfig(
                enabled=True, morphology=MorphologyConfig(enabled=True)
            ),
        )
        assert result["nlp_enabled"] is True

    def test_compare_strategies_covers_all_runs(self, tmp_path):
        report = compare_strategies(V2_DIR, tmp_path)
        assert set(report["runs"]) == {"fixed_char", "semantic", "semantic+nlp"}
        assert (tmp_path / "chunk-benchmark.json").exists()

    def test_shape_health_helper(self):
        healthy = ChunkShapeStats(
            total_chunks=10,
            documents=2,
            chunks_per_document=5.0,
            mean_tokens=50.0,
            min_tokens=10,
            max_tokens=100,
            empty_chunks=0,
            sentence_boundary_rate=0.95,
        )
        assert healthy.is_healthy
        assert not ChunkShapeStats(
            total_chunks=10,
            documents=2,
            chunks_per_document=5.0,
            mean_tokens=50.0,
            min_tokens=10,
            max_tokens=100,
            empty_chunks=1,
            sentence_boundary_rate=0.95,
        ).is_healthy

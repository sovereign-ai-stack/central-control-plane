"""Benchmark infrastructure tests — no production model selection."""

from __future__ import annotations

from pathlib import Path

import pytest
from benchmarks.persian.dataset import load_dataset, query_category
from benchmarks.persian.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from benchmarks.persian.validate_dataset import validate_dataset

from rag.embedding.config import list_candidates, load_candidate_config

REPO_ROOT = Path(__file__).resolve().parents[4]
DATASET_DIR = REPO_ROOT / "benchmarks" / "persian" / "data" / "fa-retrieval-v1"
CANDIDATES_PATH = REPO_ROOT / "benchmarks" / "persian" / "config" / "candidates.yaml"


@pytest.fixture(scope="session", autouse=True)
def ensure_dataset() -> None:
    if not (DATASET_DIR / "corpus.jsonl").exists():
        from benchmarks.persian.generate_dataset import generate_dataset

        generate_dataset(DATASET_DIR)


class TestBenchmarkInfrastructure:
    def test_dataset_validation_passes(self, ensure_dataset):
        errors = validate_dataset(DATASET_DIR)
        assert errors == []

    def test_dataset_loads(self, ensure_dataset):
        dataset = load_dataset(DATASET_DIR)
        assert len(dataset.corpus) >= 200
        assert len(dataset.validation_query_ids) >= 80

    def test_candidates_include_m0_m3(self):
        candidates = list_candidates(CANDIDATES_PATH)
        ids = {item["id"] for item in candidates}
        assert ids == {
            "M0-baseline",
            "M1-e5-large",
            "M2-bge-m3",
            "M3-persian-heydari",
        }

    def test_m3_config_not_production(self):
        config = load_candidate_config("M3-persian-heydari", CANDIDATES_PATH)
        assert config.production is False
        assert config.model_id == "heydariAI/persian-embeddings"

    def test_metrics_helpers(self):
        relevant = {"d1", "d2"}
        ranked = ["d3", "d1", "d2"]
        assert recall_at_k(relevant, ranked, 1) == 0.0
        assert recall_at_k(relevant, ranked, 2) == 1.0
        assert reciprocal_rank(relevant, ranked) == 0.5
        assert precision_at_k(relevant, ranked, 3) == pytest.approx(2 / 3)
        assert ndcg_at_k(relevant, ranked, 3) > 0.0

    def test_query_category_mapping(self, ensure_dataset):
        dataset = load_dataset(DATASET_DIR)
        categories = {query_category(query) for query in dataset.queries}
        assert "semantic" in categories
        assert "zwnj" in categories

    def test_benchmark_dry_run(self, ensure_dataset, tmp_path):
        from benchmarks.persian.run_benchmark import run_benchmark

        summary = run_benchmark(
            dataset_dir=DATASET_DIR,
            candidates_path=CANDIDATES_PATH,
            output_dir=tmp_path / "results",
            device="cpu",
            seed=42,
            split="val",
            dry_run=True,
        )
        assert summary["dry_run"] is True
        assert len(summary["candidates"]) == 4

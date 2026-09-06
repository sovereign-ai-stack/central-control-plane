"""
Before/after comparison for the Persian NLP layer.

Runs the same model over the same dataset in two or more NLP modes and reports
Recall@5, MRR, and nDCG deltas overall and per category. This is the evidence
that decides whether morphology is enabled in production — it ships measured,
not assumed.

Usage:

    python -m benchmarks.persian.compare_nlp \\
        --dataset benchmarks/persian/data/fa-retrieval-v2 \\
        --candidates benchmarks/persian/config/candidates.yaml \\
        --candidate M2-bge-m3 \\
        --output benchmarks/persian/results/nlp-ab

The `stub` candidate needs no model download and exercises the mechanics only;
its scores are not a quality signal.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from benchmarks.persian.dataset import BenchmarkDataset, load_dataset, query_category
from benchmarks.persian.evaluate import build_query_metrics, encode_corpus, rank_query
from benchmarks.persian.metrics import AggregateMetrics, aggregate_query_metrics
from rag.embedding.config import EmbeddingConfig, load_candidate_config
from rag.embedding.errors import EmbeddingModelLoadError
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.embedding.stub import StubEmbeddingModel
from rag.nlp.config import MorphologyConfig, NlpConfig
from rag.nlp.pipeline import PersianNlpPipeline

MODES = ("off", "on", "morphology")
K_VALUES = [1, 3, 5, 10, 20]
NDCG_K_VALUES = [5, 10]

MORPHOLOGY_CATEGORIES = (
    "morphology",
    "plural_forms",
    "verb_forms",
    "spelling_variants",
    "zwnj",
    "arabic_char_variants",
)


@dataclass(frozen=True, slots=True)
class ModeResult:
    mode: str
    aggregate: AggregateMetrics
    normalization_version: str
    morphology_enabled: bool


def nlp_config_for(mode: str) -> NlpConfig | None:
    if mode == "off":
        return None
    if mode == "on":
        return NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=False))
    if mode == "morphology":
        return NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=True))
    raise ValueError(f"unknown mode: {mode!r}")


def _build_service(
    candidate_id: str,
    candidates_path: Path,
    device: str,
    nlp_config: NlpConfig | None,
) -> tuple[EmbeddingService, str]:
    pipeline = (
        PersianNlpPipeline(nlp_config)
        if nlp_config is not None and nlp_config.enabled
        else None
    )
    if candidate_id == "stub":
        model = StubEmbeddingModel(dimension=384, model_id="stub-v1")
        version = "fa-norm-v1"
    else:
        config: EmbeddingConfig = load_candidate_config(
            candidate_id, candidates_path, device=device
        )
        model = ModelRegistry.create(config)
        version = config.preprocessing.normalization_version
    if pipeline is not None:
        version = pipeline.config.normalization_version
    preprocessor = EmbeddingPreprocessor(version, nlp=pipeline)
    return EmbeddingService(model, preprocessor), version


def evaluate_mode(
    mode: str,
    dataset: BenchmarkDataset,
    *,
    candidate_id: str,
    candidates_path: Path,
    device: str,
    split: str,
) -> ModeResult:
    nlp_config = nlp_config_for(mode)
    service, version = _build_service(candidate_id, candidates_path, device, nlp_config)

    doc_ids, doc_matrix, corpus_text = encode_corpus(service, dataset)
    selected = (
        dataset.validation_query_ids if split == "val" else dataset.test_query_ids
    )

    per_query = []
    for query in dataset.queries:
        if query.query_id not in selected:
            continue
        ranked_ids, _hits = rank_query(
            service, query.text, doc_ids, doc_matrix, corpus_text
        )
        per_query.append(
            build_query_metrics(
                query.query_id,
                query_category(query),
                query.relevant_doc_ids,
                ranked_ids,
                k_values=K_VALUES,
                ndcg_k_values=NDCG_K_VALUES,
            )
        )

    return ModeResult(
        mode=mode,
        aggregate=aggregate_query_metrics(
            per_query, k_values=K_VALUES, ndcg_k_values=NDCG_K_VALUES
        ),
        normalization_version=version,
        morphology_enabled=bool(
            nlp_config is not None and nlp_config.morphology.enabled
        ),
    )


def build_comparison(results: list[ModeResult]) -> dict[str, Any]:
    baseline = next(item for item in results if item.mode == "off")

    def headline(result: ModeResult) -> dict[str, float]:
        return {
            "recall_at_5": round(result.aggregate.recall_at_k.get(5, 0.0), 4),
            "mrr": round(result.aggregate.mrr, 4),
            "ndcg_at_5": round(result.aggregate.ndcg_at_k.get(5, 0.0), 4),
            "ndcg_at_10": round(result.aggregate.ndcg_at_k.get(10, 0.0), 4),
        }

    base = headline(baseline)
    modes: dict[str, Any] = {}
    for result in results:
        current = headline(result)
        modes[result.mode] = {
            "metrics": current,
            "delta_vs_off": {
                key: round(current[key] - base[key], 4) for key in current
            },
            "normalization_version": result.normalization_version,
            "morphology_enabled": result.morphology_enabled,
            "by_category": {
                category: {
                    "recall_at_5": round(values.get("recall_at_5", 0.0), 4),
                    "mrr": round(values.get("mrr", 0.0), 4),
                    "delta_recall_at_5": round(
                        values.get("recall_at_5", 0.0)
                        - baseline.aggregate.by_category.get(category, {}).get(
                            "recall_at_5", 0.0
                        ),
                        4,
                    ),
                }
                for category, values in sorted(result.aggregate.by_category.items())
            },
        }
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "baseline_mode": "off",
        "modes": modes,
    }


def render_markdown(comparison: dict[str, Any], candidate_id: str) -> str:
    lines = [
        f"# Persian NLP layer A/B — `{candidate_id}`",
        "",
        f"Generated: {comparison['generated_at']}",
        "",
        "## Headline metrics",
        "",
        "| Mode | Recall@5 | MRR | nDCG@5 | nDCG@10 |",
        "|------|----------|-----|--------|---------|",
    ]
    for mode, payload in comparison["modes"].items():
        metrics = payload["metrics"]
        delta = payload["delta_vs_off"]
        suffix = "" if mode == "off" else f" ({delta['recall_at_5']:+.4f})"
        lines.append(
            f"| {mode} | {metrics['recall_at_5']:.4f}{suffix} | "
            f"{metrics['mrr']:.4f} | {metrics['ndcg_at_5']:.4f} | "
            f"{metrics['ndcg_at_10']:.4f} |"
        )

    lines += ["", "## Morphology-sensitive categories (Recall@5 delta vs off)", ""]
    header_modes = [m for m in comparison["modes"] if m != "off"]
    lines.append("| Category | " + " | ".join(header_modes) + " |")
    lines.append("|----------|" + "|".join(["-------"] * len(header_modes)) + "|")
    categories = sorted(
        {
            category
            for payload in comparison["modes"].values()
            for category in payload["by_category"]
        }
    )
    for category in categories:
        if category not in MORPHOLOGY_CATEGORIES:
            continue
        cells = []
        for mode in header_modes:
            entry = comparison["modes"][mode]["by_category"].get(category)
            cells.append(f"{entry['delta_recall_at_5']:+.4f}" if entry else "n/a")
        lines.append(f"| {category} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## Interpretation",
        "",
        "A positive delta on the morphology categories with a non-negative delta on",
        "the headline metrics is the evidence required to enable morphology in",
        "`config/nlp.yaml`. A negative headline delta means over-stemming is costing",
        "more recall than inflection matching gains, and the default stays off.",
        "",
    ]
    return "\n".join(lines)


def run_comparison(
    *,
    dataset_dir: Path,
    candidates_path: Path,
    output_dir: Path,
    candidate_id: str,
    device: str = "cpu",
    split: str = "val",
    modes: tuple[str, ...] = MODES,
) -> dict[str, Any]:
    dataset = load_dataset(dataset_dir)
    results: list[ModeResult] = []
    for mode in modes:
        print(f"Evaluating NLP mode: {mode}...", file=sys.stderr)
        results.append(
            evaluate_mode(
                mode,
                dataset,
                candidate_id=candidate_id,
                candidates_path=candidates_path,
                device=device,
                split=split,
            )
        )

    comparison = build_comparison(results)
    comparison["candidate"] = candidate_id
    comparison["dataset"] = dataset.dataset_version
    comparison["split"] = split

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "nlp-comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "nlp-comparison.md").write_text(
        render_markdown(comparison, candidate_id), encoding="utf-8"
    )
    return comparison


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare retrieval with/without NLP")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candidate", default="stub")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES))
    args = parser.parse_args(argv)

    try:
        comparison = run_comparison(
            dataset_dir=args.dataset,
            candidates_path=args.candidates,
            output_dir=args.output,
            candidate_id=args.candidate,
            device=args.device,
            split=args.split,
            modes=tuple(args.modes),
        )
    except (EmbeddingModelLoadError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(render_markdown(comparison, args.candidate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Persian embedding benchmark runner."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from benchmarks.persian.dataset import BenchmarkDataset, load_dataset, query_category
from benchmarks.persian.metrics import (
    AggregateMetrics,
    QueryMetrics,
    aggregate_query_metrics,
    cosine_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from benchmarks.persian.validate_dataset import validate_dataset
from rag.embedding.config import EmbeddingConfig, load_candidate_config
from rag.embedding.errors import EmbeddingError, EmbeddingModelLoadError
from rag.embedding.metrics import EmbeddingMetrics
from rag.embedding.preprocessor import EmbeddingPreprocessor
from rag.embedding.registry import ModelRegistry
from rag.embedding.service import EmbeddingService
from rag.nlp.config import MorphologyConfig, NlpConfig
from rag.nlp.pipeline import PersianNlpPipeline


@dataclass
class PerformanceStats:
    load_time_sec: float
    runtime_dimension: int
    dimension_source: str
    query_latency_ms: dict[str, float]
    throughput_chunks_per_sec: float
    peak_rss_mb: float | None
    peak_vram_mb: float | None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            cwd=_repo_root(),
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _hardware_profile(device: str) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "cpu": platform.processor() or platform.machine(),
        "ram_gb": None,
        "gpu": device if device.startswith("cuda") else None,
        "os": platform.platform(),
        "python": platform.python_version(),
        "torch": None,
        "cuda": None,
    }
    try:
        import torch

        profile["torch"] = torch.__version__
        if torch.cuda.is_available():
            profile["cuda"] = torch.version.cuda
            profile["gpu"] = torch.cuda.get_device_name(0)
    except ImportError:
        pass
    return profile


def _peak_rss_mb() -> float | None:
    """
    Peak resident set size in MB, or None if the platform cannot report it.

    `resource` does not exist on Windows, which silently produced None for every
    candidate. Windows is handled through psapi instead so the benchmark's
    memory metric is actually populated.
    """
    if sys.platform.startswith("win"):
        return _peak_rss_mb_windows()
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(usage / 1024, 2)
    except Exception:  # noqa: BLE001 - memory reporting is best effort
        return None


def _peak_rss_mb_windows() -> float | None:
    import ctypes
    from ctypes import wintypes

    class _ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    try:
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(_ProcessMemoryCounters)
        query = ctypes.windll.kernel32.K32GetProcessMemoryInfo
        query.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not query(handle, ctypes.byref(counters), counters.cb):
            return None
        return round(counters.PeakWorkingSetSize / (1024 * 1024), 2)
    except Exception:  # noqa: BLE001 - memory reporting is best effort
        return None


def _evaluate_model(
    service: EmbeddingService,
    dataset: BenchmarkDataset,
    *,
    split: str,
    k_values: list[int],
    ndcg_k_values: list[int],
) -> tuple[list[QueryMetrics], PerformanceStats]:
    split_ids = (
        dataset.validation_query_ids if split == "val" else dataset.test_query_ids
    )
    queries = [query for query in dataset.queries if query.query_id in split_ids]

    doc_ids = [doc.doc_id for doc in dataset.corpus]
    texts = [doc.text for doc in dataset.corpus]
    doc_result = service.embed_documents(texts)
    doc_matrix = np.vstack(doc_result.vectors) if doc_result.vectors else np.empty((0, 0))

    per_query: list[QueryMetrics] = []
    query_latencies: list[float] = []
    for query in queries:
        query_result = service.embed_query(query.text)
        query_latencies.append(query_result.latency_ms)
        ranked = cosine_rank(query_result.vector, doc_ids, doc_matrix)
        relevant = set(query.relevant_doc_ids)
        row = QueryMetrics(
            query_id=query.query_id,
            category=query_category(query),
            reciprocal_rank=reciprocal_rank(relevant, ranked),
        )
        for k in k_values:
            row.recall_at_k[k] = recall_at_k(relevant, ranked, k)
        for k in (5, 10):
            if k in k_values or k in ndcg_k_values:
                row.precision_at_k[k] = precision_at_k(relevant, ranked, k)
        for k in ndcg_k_values:
            row.ndcg_at_k[k] = ndcg_at_k(relevant, ranked, k)
        per_query.append(row)

    warmup = min(20, len(queries))
    for query in queries[:warmup]:
        service.embed_query(query.text)
    timed_latencies: list[float] = []
    for query in queries[: min(500, len(queries))]:
        result = service.embed_query(query.text)
        timed_latencies.append(result.latency_ms)

    timed_latencies.sort()
    def percentile(values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        index = int(round((pct / 100) * (len(values) - 1)))
        return values[index]

    throughput_started = time.perf_counter()
    batch_texts = texts[: min(128, len(texts))]
    service.embed_documents(batch_texts)
    throughput_elapsed = max(time.perf_counter() - throughput_started, 1e-6)

    info = service.model_info
    perf = PerformanceStats(
        load_time_sec=0.0,
        runtime_dimension=info.dimension,
        dimension_source="model.info.dimension",
        query_latency_ms={
            "p50": percentile(timed_latencies, 50),
            "p95": percentile(timed_latencies, 95),
            "p99": percentile(timed_latencies, 99),
        },
        throughput_chunks_per_sec=round(len(batch_texts) / throughput_elapsed, 2),
        peak_rss_mb=_peak_rss_mb(),
        peak_vram_mb=None,
    )
    _ = query_latencies
    return per_query, perf


def _run_candidate(
    candidate_id: str,
    dataset: BenchmarkDataset,
    *,
    candidates_path: Path,
    device: str,
    seed: int,
    split: str,
    k_values: list[int],
    ndcg_k_values: list[int],
    nlp_config: NlpConfig | None = None,
) -> dict[str, Any] | None:
    config = load_candidate_config(candidate_id, candidates_path, device=device)
    config = EmbeddingConfig(
        backend=config.backend,
        model_id=config.model_id,
        revision=config.revision,
        device=device,
        batch_size=config.batch_size,
        normalize_embeddings=config.normalize_embeddings,
        query_prefix=config.query_prefix,
        document_prefix=config.document_prefix,
        torch_seed=seed,
        max_sequence_length=config.max_sequence_length,
        preprocessing=config.preprocessing,
        candidate_id=candidate_id,
        production=config.production,
        load_timeout_sec=config.load_timeout_sec,
        strict_load=config.strict_load,
    )

    load_started = time.perf_counter()
    try:
        model = ModelRegistry.create(config)
    except EmbeddingModelLoadError as exc:
        print(f"SKIP {candidate_id}: load failed ({exc})", file=sys.stderr)
        return None
    load_time_sec = time.perf_counter() - load_started

    nlp_pipeline = (
        PersianNlpPipeline(nlp_config)
        if nlp_config is not None and nlp_config.enabled
        else None
    )
    normalization_version = (
        nlp_pipeline.config.normalization_version
        if nlp_pipeline is not None
        else config.preprocessing.normalization_version
    )
    preprocessor = EmbeddingPreprocessor(normalization_version, nlp=nlp_pipeline)
    service = EmbeddingService(model, preprocessor, EmbeddingMetrics())
    per_query, perf = _evaluate_model(
        service,
        dataset,
        split=split,
        k_values=k_values,
        ndcg_k_values=ndcg_k_values,
    )
    perf.load_time_sec = round(load_time_sec, 3)
    aggregate = aggregate_query_metrics(
        per_query, k_values=k_values, ndcg_k_values=ndcg_k_values
    )
    payload = _result_payload(candidate_id, config, aggregate, perf)
    payload["nlp"] = {
        "enabled": nlp_pipeline is not None,
        "version": nlp_pipeline.version if nlp_pipeline is not None else None,
        "morphology": (
            nlp_pipeline.config.morphology.enabled if nlp_pipeline is not None else False
        ),
        "normalization_version": normalization_version,
    }
    return payload


def _result_payload(
    candidate_id: str,
    config: EmbeddingConfig,
    aggregate: AggregateMetrics,
    perf: PerformanceStats,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "model_id": config.model_id,
        "revision": config.revision,
        "production": config.production,
        "dimension": perf.runtime_dimension,
        "dimension_source": perf.dimension_source,
        "recall_at_k": {str(k): v for k, v in aggregate.recall_at_k.items()},
        "precision_at_k": {str(k): v for k, v in aggregate.precision_at_k.items()},
        "mrr": aggregate.mrr,
        "ndcg_at_k": {str(k): v for k, v in aggregate.ndcg_at_k.items()},
        "latency_ms": perf.query_latency_ms,
        "throughput_chunks_per_sec": perf.throughput_chunks_per_sec,
        "peak_rss_mb": perf.peak_rss_mb,
        "peak_vram_mb": perf.peak_vram_mb,
        "load_time_sec": perf.load_time_sec,
        "by_category": aggregate.by_category,
    }


def run_benchmark(
    *,
    dataset_dir: Path,
    candidates_path: Path,
    output_dir: Path,
    device: str,
    seed: int,
    split: str,
    dry_run: bool = False,
    nlp_config: NlpConfig | None = None,
) -> dict[str, Any]:
    errors = validate_dataset(dataset_dir)
    if errors:
        raise RuntimeError("Dataset validation failed:\n" + "\n".join(errors))

    with candidates_path.open(encoding="utf-8") as handle:
        candidates_yaml = yaml.safe_load(handle)
    benchmark_cfg = candidates_yaml.get("benchmark", {})
    k_values = list(benchmark_cfg.get("k_values", [1, 3, 5, 10, 20]))
    ndcg_k_values = list(benchmark_cfg.get("ndcg_k_values", [5, 10]))

    if dry_run:
        return {
            "dry_run": True,
            "dataset": str(dataset_dir),
            "candidates": [item["id"] for item in candidates_yaml.get("candidates", [])],
        }

    dataset = load_dataset(dataset_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_results: list[dict[str, Any]] = []
    for candidate in candidates_yaml.get("candidates", []):
        candidate_id = candidate["id"]
        print(f"Running candidate {candidate_id}...")
        result = _run_candidate(
            candidate_id,
            dataset,
            candidates_path=candidates_path,
            device=device,
            seed=seed,
            split=split,
            k_values=k_values,
            ndcg_k_values=ndcg_k_values,
            nlp_config=nlp_config,
        )
        if result is None:
            continue
        model_results.append(result)
        with (output_dir / f"{candidate_id}.json").open("w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)

    summary = {
        "benchmark_version": "1.0.0",
        "dataset_version": dataset.dataset_version,
        "git_commit": _git_commit(),
        "hardware_profile": _hardware_profile(device),
        "normalization_version": benchmark_cfg.get("normalization_version", "fa-norm-v1"),
        "timestamp": datetime.now(UTC).isoformat(),
        "split": split,
        "models": model_results,
        "selected_model": None,
        "selection_rationale": None,
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    lines = [
        "# Persian Embedding Benchmark Summary",
        "",
        f"- Dataset: `{dataset.dataset_version}`",
        f"- Split: `{split}`",
        f"- Models evaluated: {len(model_results)}",
        "",
        "## Results",
        "",
    ]
    for result in model_results:
        recall5 = result["recall_at_k"].get("5", 0.0)
        lines.append(
            f"- **{result['candidate_id']}**: dim={result['dimension']}, "
            f"Recall@5={recall5:.4f}, MRR={result['mrr']:.4f}, "
            f"load={result['load_time_sec']}s"
        )
    lines.append("")
    lines.append("**Production model NOT selected** — awaiting human sign-off.")
    (output_dir / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def build_nlp_config(mode: str) -> NlpConfig | None:
    """Map the --nlp flag to a config. "off" returns None (pre-Phase-5 baseline)."""
    if mode == "off":
        return None
    if mode == "on":
        return NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=False))
    if mode == "morphology":
        return NlpConfig(enabled=True, morphology=MorphologyConfig(enabled=True))
    raise ValueError(f"unknown nlp mode: {mode!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Persian embedding benchmark")
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--split", choices=("val", "test"), default="val")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--nlp",
        choices=("off", "on", "morphology"),
        default="off",
        help="Persian NLP layer: off (baseline), on (fa-norm-v2), "
        "morphology (fa-norm-v2 + lemmatization)",
    )
    args = parser.parse_args(argv)

    nlp_config = build_nlp_config(args.nlp)

    try:
        run_benchmark(
            dataset_dir=args.dataset,
            candidates_path=args.candidates,
            output_dir=args.output,
            device=args.device,
            seed=args.seed,
            split=args.split,
            dry_run=args.dry_run,
            nlp_config=nlp_config,
        )
    except (RuntimeError, EmbeddingError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

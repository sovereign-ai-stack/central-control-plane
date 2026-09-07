"""Configuration loading for embedding service."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rag.embedding.errors import EmbeddingModelLoadError


@dataclass(frozen=True, slots=True)
class PreprocessingConfig:
    normalization_version: str = "fa-norm-v1"
    digit_mode: str = "preserve"


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    backend: str
    model_id: str
    revision: str | None = None
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True
    query_prefix: str | None = None
    document_prefix: str | None = None
    torch_seed: int | None = 42
    max_sequence_length: int | None = None
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    candidate_id: str | None = None
    production: bool = False
    # Seconds allowed for backend model load. None keeps the serving defaults
    # (short, fail-fast). Offline work such as the benchmark needs a real
    # budget: a cold 1 GB checkpoint does not load in six seconds.
    load_timeout_sec: float | None = None
    # True forbids the ModelRegistry stub fallback. A benchmark that silently
    # measures StubEmbeddingModel reports fiction, so it must fail loudly.
    strict_load: bool = False


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise EmbeddingModelLoadError(f"Invalid YAML config: {path}")
    return data


def load_embedding_config(path: Path | None = None) -> EmbeddingConfig:
    config_path = path or _repo_root() / "config" / "embedding.yaml"
    raw = load_yaml(config_path)
    block = raw.get("embedding")
    if not isinstance(block, dict):
        raise EmbeddingModelLoadError(f"Missing 'embedding' section in {config_path}")
    return _config_from_mapping(block)


def load_candidate_config(
    candidate_id: str,
    candidates_path: Path | None = None,
    *,
    device: str | None = None,
    batch_size: int | None = None,
) -> EmbeddingConfig:
    path = candidates_path or _repo_root() / "benchmarks" / "persian" / "config" / "candidates.yaml"
    raw = load_yaml(path)
    candidates = raw.get("candidates", [])
    benchmark = raw.get("benchmark", {})
    match = next((item for item in candidates if item.get("id") == candidate_id), None)
    if match is None:
        raise EmbeddingModelLoadError(f"Unknown candidate id: {candidate_id}")

    preprocessing = PreprocessingConfig(
        normalization_version=str(benchmark.get("normalization_version", "fa-norm-v1"))
    )
    return EmbeddingConfig(
        backend=str(match["backend"]),
        model_id=str(match["model_id"]),
        revision=match.get("revision"),
        device=device or str(benchmark.get("device", "cpu")),
        batch_size=batch_size or int(benchmark.get("batch_size", 32)),
        normalize_embeddings=bool(benchmark.get("normalize_embeddings", True)),
        query_prefix=match.get("query_prefix"),
        document_prefix=match.get("document_prefix"),
        torch_seed=int(benchmark.get("seed", 42)),
        preprocessing=preprocessing,
        candidate_id=candidate_id,
        production=bool(match.get("production", False)),
        load_timeout_sec=(
            float(benchmark["load_timeout_sec"])
            if benchmark.get("load_timeout_sec") is not None
            else None
        ),
        strict_load=bool(benchmark.get("strict_load", False)),
    )


def list_candidates(candidates_path: Path | None = None) -> list[dict[str, Any]]:
    path = candidates_path or _repo_root() / "benchmarks" / "persian" / "config" / "candidates.yaml"
    raw = load_yaml(path)
    candidates = raw.get("candidates", [])
    if not isinstance(candidates, list):
        raise EmbeddingModelLoadError("Invalid candidates.yaml")
    return candidates


def _config_from_mapping(block: dict[str, Any]) -> EmbeddingConfig:
    preprocessing_raw = block.get("preprocessing", {})
    preprocessing = PreprocessingConfig(
        normalization_version=str(preprocessing_raw.get("normalization_version", "fa-norm-v1")),
        digit_mode=str(preprocessing_raw.get("digit_mode", "preserve")),
    )
    import os
    env_backend = os.getenv("RAG_EMBEDDING_BACKEND")
    backend = env_backend or block.get("backend") or block.get("provider")
    if backend == "local":
        backend = "sentence-transformers"
    model_id = block.get("model_id")
    if model_id is None and block.get("model"):
        return load_candidate_config(str(block["model"]), device=block.get("device"))
    if model_id is None:
        model_id = "default-embedding-model"
    if backend is None:
        backend = "stub"
    return EmbeddingConfig(
        backend=str(backend),
        model_id=str(model_id),
        revision=block.get("revision"),
        device=str(block.get("device", "cpu")),
        batch_size=int(block.get("batch_size", 32)),
        normalize_embeddings=bool(block.get("normalize_embeddings", True)),
        query_prefix=block.get("query_prefix"),
        document_prefix=block.get("document_prefix"),
        torch_seed=block.get("torch_seed", 42),
        max_sequence_length=block.get("max_sequence_length"),
        preprocessing=preprocessing,
        production=bool(block.get("production", False)),
        load_timeout_sec=(
            float(block["load_timeout_sec"])
            if block.get("load_timeout_sec") is not None
            else None
        ),
        strict_load=bool(block.get("strict_load", False)),
    )

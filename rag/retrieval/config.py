"""Retrieval quality pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag.retrieval.errors import RetrievalValidationError

MAX_FINAL_K = 50
MAX_CANDIDATE_K = 100


@dataclass(frozen=True, slots=True)
class RetrievalConfig:
    """Deterministic reranking and context assembly settings."""

    candidate_k: int = 30
    final_k: int = 10
    semantic_weight: float = 0.7
    lexical_weight: float = 0.2
    phrase_weight: float = 0.1
    max_chunks_per_document: int | None = None
    max_context_chars: int = 8000

    def validate_k(self, *, candidate_k: int, final_k: int) -> None:
        if final_k <= 0:
            raise RetrievalValidationError("final_k must be positive")
        if candidate_k <= 0:
            raise RetrievalValidationError("candidate_k must be positive")
        if candidate_k < final_k:
            raise RetrievalValidationError("candidate_k must be >= final_k")
        if final_k > MAX_FINAL_K:
            raise RetrievalValidationError(f"final_k must not exceed {MAX_FINAL_K}")
        if candidate_k > MAX_CANDIDATE_K:
            raise RetrievalValidationError(
                f"candidate_k must not exceed {MAX_CANDIDATE_K}"
            )


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_retrieval_config(path: Path | None = None) -> RetrievalConfig:
    config_path = path or _repo_root() / "config" / "retrieval.yaml"
    if not config_path.exists():
        return RetrievalConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return RetrievalConfig()
    block = raw.get("retrieval", raw)
    if not isinstance(block, dict):
        return RetrievalConfig()
    return _from_mapping(block)


def _from_mapping(block: dict[str, Any]) -> RetrievalConfig:
    max_per_doc = block.get("max_chunks_per_document")
    return RetrievalConfig(
        candidate_k=int(block.get("candidate_k", 30)),
        final_k=int(block.get("final_k", 10)),
        semantic_weight=float(block.get("semantic_weight", 0.7)),
        lexical_weight=float(block.get("lexical_weight", 0.2)),
        phrase_weight=float(block.get("phrase_weight", 0.1)),
        max_chunks_per_document=(
            int(max_per_doc) if max_per_doc is not None else None
        ),
        max_context_chars=int(block.get("max_context_chars", 8000)),
    )

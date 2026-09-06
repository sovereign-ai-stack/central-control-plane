"""Post-retrieval pipeline configuration (spec 005-rag-pipeline/reranker.md §6)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag.pipeline.errors import PipelineValidationError
from rag.pipeline.types import CONTEXT_FORMAT_DELIMITED_V1, PipelineOptions

MAX_TOP_K = 50
MAX_CONTEXT_TOKENS = 32_768
MAX_CANDIDATE_POOL_K = 50

BACKEND_NOOP = "noop"
BACKEND_LEXICAL = "lexical"
SUPPORTED_BACKENDS = frozenset({BACKEND_NOOP, BACKEND_LEXICAL})


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """
    Deterministic post-retrieval defaults.

    `rerank_model_id` stays null: production reranker model selection is deferred
    to a benchmark (reranker.md §4.2) and is not part of this configuration.
    """

    rerank: bool = False
    backend: str = BACKEND_NOOP
    rerank_model_id: str | None = None
    max_candidates: int = 50
    candidate_pool_k: int = 30
    top_k: int = 10
    max_context_tokens: int = 4096
    dedupe_by_content_hash: bool = True
    context_format: str = CONTEXT_FORMAT_DELIMITED_V1
    chars_per_token: int = 4
    retrieval_weight: float = 0.5
    lexical_weight: float = 0.3
    phrase_weight: float = 0.2
    strict_authorization: bool = False

    def to_options(
        self,
        *,
        rerank: bool | None = None,
        top_k: int | None = None,
        max_context_tokens: int | None = None,
    ) -> PipelineOptions:
        """Build request options from configured defaults, clamping caller limits."""
        requested_tokens = (
            self.max_context_tokens if max_context_tokens is None else max_context_tokens
        )
        return PipelineOptions(
            rerank=self.rerank if rerank is None else rerank,
            top_k=self.top_k if top_k is None else top_k,
            max_context_tokens=min(requested_tokens, self.max_context_tokens),
            dedupe_by_content_hash=self.dedupe_by_content_hash,
            context_format=self.context_format,
        )


def validate_options(options: PipelineOptions) -> None:
    """Fail closed on limits that would produce empty or excessive context."""
    if options.top_k <= 0:
        raise PipelineValidationError("top_k must be positive")
    if options.top_k > MAX_TOP_K:
        raise PipelineValidationError(f"top_k must not exceed {MAX_TOP_K}")
    if options.max_context_tokens <= 0:
        raise PipelineValidationError("max_context_tokens must be positive")
    if options.max_context_tokens > MAX_CONTEXT_TOKENS:
        raise PipelineValidationError(
            f"max_context_tokens must not exceed {MAX_CONTEXT_TOKENS}"
        )
    if options.context_format != CONTEXT_FORMAT_DELIMITED_V1:
        raise PipelineValidationError(
            f"unsupported context format {options.context_format!r}"
        )


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_pipeline_config(path: Path | None = None) -> PipelineConfig:
    config_path = path or _repo_root() / "config" / "pipeline.yaml"
    if not config_path.exists():
        return PipelineConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return PipelineConfig()
    block = raw.get("pipeline", raw)
    if not isinstance(block, dict):
        return PipelineConfig()
    return _from_mapping(block)


def _from_mapping(block: dict[str, Any]) -> PipelineConfig:
    backend = str(block.get("backend", BACKEND_NOOP))
    if backend not in SUPPORTED_BACKENDS:
        raise PipelineValidationError(f"unsupported reranker backend {backend!r}")
    model_id = block.get("model_id")
    config = PipelineConfig(
        rerank=bool(block.get("rerank", False)),
        backend=backend,
        rerank_model_id=str(model_id) if model_id is not None else None,
        max_candidates=int(block.get("max_candidates", 50)),
        candidate_pool_k=int(block.get("candidate_pool_k", 30)),
        top_k=int(block.get("top_k", 10)),
        max_context_tokens=int(block.get("max_context_tokens", 4096)),
        dedupe_by_content_hash=bool(block.get("dedupe_by_content_hash", True)),
        context_format=str(block.get("context_format", CONTEXT_FORMAT_DELIMITED_V1)),
        chars_per_token=int(block.get("chars_per_token", 4)),
        retrieval_weight=float(block.get("retrieval_weight", 0.5)),
        lexical_weight=float(block.get("lexical_weight", 0.3)),
        phrase_weight=float(block.get("phrase_weight", 0.2)),
        strict_authorization=bool(block.get("strict_authorization", False)),
    )
    _validate_config(config)
    return config


def _validate_config(config: PipelineConfig) -> None:
    if config.chars_per_token <= 0:
        raise PipelineValidationError("chars_per_token must be positive")
    if config.max_candidates <= 0:
        raise PipelineValidationError("max_candidates must be positive")
    if config.candidate_pool_k <= 0:
        raise PipelineValidationError("candidate_pool_k must be positive")
    if config.candidate_pool_k > MAX_CANDIDATE_POOL_K:
        raise PipelineValidationError(
            f"candidate_pool_k must not exceed {MAX_CANDIDATE_POOL_K}"
        )
    if config.candidate_pool_k < config.top_k:
        raise PipelineValidationError("candidate_pool_k must be >= top_k")
    validate_options(config.to_options())

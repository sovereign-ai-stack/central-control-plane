"""
Chunking configuration.

The default strategy stays `fixed_char`, which is the pre-Phase-5 behaviour, so
enabling semantic chunking is an explicit, reversible decision. Chunk size is
expressed in **word tokens** for the semantic strategy and characters for the
legacy one, because the two measure different things and silently reusing one
number for both would misconfigure whichever came second.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag.ingestion.chunker import DEFAULT_MAX_CHUNK_CHARS
from rag.ingestion.errors import IngestValidationError

STRATEGY_FIXED_CHAR = "fixed_char"
STRATEGY_SEMANTIC = "semantic"
SUPPORTED_STRATEGIES = (STRATEGY_FIXED_CHAR, STRATEGY_SEMANTIC)

MAX_TOKENS_CEILING = 2_000


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    strategy: str = STRATEGY_FIXED_CHAR
    max_tokens: int = 220
    overlap_tokens: int = 40
    min_chunk_tokens: int = 25
    respect_sentences: bool = True
    respect_structure: bool = True
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS

    def validate(self) -> None:
        if self.strategy not in SUPPORTED_STRATEGIES:
            raise IngestValidationError(
                f"unsupported chunking strategy {self.strategy!r}; "
                f"expected one of {SUPPORTED_STRATEGIES}"
            )
        if self.max_tokens <= 0:
            raise IngestValidationError("max_tokens must be positive")
        if self.max_tokens > MAX_TOKENS_CEILING:
            raise IngestValidationError(
                f"max_tokens must not exceed {MAX_TOKENS_CEILING}"
            )
        if self.overlap_tokens < 0:
            raise IngestValidationError("overlap_tokens must not be negative")
        if self.overlap_tokens >= self.max_tokens:
            # Equal or larger overlap would never advance the cursor.
            raise IngestValidationError("overlap_tokens must be smaller than max_tokens")
        if self.min_chunk_tokens < 0:
            raise IngestValidationError("min_chunk_tokens must not be negative")
        if self.max_chars <= 0:
            raise IngestValidationError("max_chars must be positive")


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "config").is_dir():
            return parent
        if (parent / "rag" / "config").is_dir():
            return parent / "rag"
    return current.parents[1]


def load_chunking_config(path: Path | None = None) -> ChunkingConfig:
    config_path = path or _repo_root() / "config" / "chunking.yaml"
    if not config_path.exists():
        return ChunkingConfig()
    with config_path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    if not isinstance(raw, dict):
        return ChunkingConfig()
    block = raw.get("chunking", raw)
    if not isinstance(block, dict):
        return ChunkingConfig()
    return _from_mapping(block)


def _from_mapping(block: dict[str, Any]) -> ChunkingConfig:
    config = ChunkingConfig(
        strategy=str(block.get("strategy", STRATEGY_FIXED_CHAR)),
        max_tokens=int(block.get("max_tokens", 220)),
        overlap_tokens=int(block.get("overlap_tokens", 40)),
        min_chunk_tokens=int(block.get("min_chunk_tokens", 25)),
        respect_sentences=bool(block.get("respect_sentences", True)),
        respect_structure=bool(block.get("respect_structure", True)),
        max_chars=int(block.get("max_chars", DEFAULT_MAX_CHUNK_CHARS)),
    )
    config.validate()
    return config

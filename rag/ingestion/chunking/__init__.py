"""Configurable document chunking strategies."""

from rag.ingestion.chunking.config import (
    STRATEGY_FIXED_CHAR,
    STRATEGY_SEMANTIC,
    SUPPORTED_STRATEGIES,
    ChunkingConfig,
    load_chunking_config,
)
from rag.ingestion.chunking.semantic import SemanticChunker, SemanticUnit
from rag.ingestion.chunking.strategy import ChunkingStrategy, FixedCharChunker
from rag.ingestion.errors import IngestValidationError


def create_chunker(config: ChunkingConfig | None = None) -> ChunkingStrategy:
    """Build the chunking strategy named by `config.strategy`."""
    resolved = config or ChunkingConfig()
    resolved.validate()
    if resolved.strategy == STRATEGY_SEMANTIC:
        return SemanticChunker(resolved)
    if resolved.strategy == STRATEGY_FIXED_CHAR:
        return FixedCharChunker(resolved)
    raise IngestValidationError(f"unsupported chunking strategy {resolved.strategy!r}")


__all__ = [
    "STRATEGY_FIXED_CHAR",
    "STRATEGY_SEMANTIC",
    "SUPPORTED_STRATEGIES",
    "ChunkingConfig",
    "ChunkingStrategy",
    "FixedCharChunker",
    "SemanticChunker",
    "SemanticUnit",
    "create_chunker",
    "load_chunking_config",
]

"""Embedding core types."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

Vector = np.ndarray


@dataclass(frozen=True, slots=True)
class ModelInfo:
    model_id: str
    revision: str | None
    dimension: int
    max_sequence_length: int
    normalization_version: str
    query_prefix: str | None
    document_prefix: str | None
    device: str
    backend: str
    normalize_embeddings: bool = True


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: list[Vector]
    model_info: ModelInfo
    latency_ms: float
    batch_size: int


@dataclass(frozen=True, slots=True)
class QueryEmbeddingResult:
    vector: Vector
    model_info: ModelInfo
    latency_ms: float

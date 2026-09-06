"""Sentence-transformers backend — local inference only."""

from __future__ import annotations

import time
from collections.abc import Sequence

import numpy as np

from rag.embedding.config import EmbeddingConfig
from rag.embedding.errors import (
    EmbeddingDeviceError,
    EmbeddingInferenceError,
    EmbeddingModelLoadError,
)
from rag.embedding.types import EmbeddingResult, ModelInfo, QueryEmbeddingResult, Vector


class SentenceTransformersBackend:
    """Generic local sentence-transformers adapter with prefix and batch support."""

    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = self._load_model(config)
        self._dimension = int(self._model.get_sentence_embedding_dimension())
        max_seq = getattr(self._model, "max_seq_length", None)
        self._max_sequence_length = int(max_seq) if max_seq is not None else 512
        self._info = ModelInfo(
            model_id=config.model_id,
            revision=config.revision,
            dimension=self._dimension,
            max_sequence_length=self._max_sequence_length,
            normalization_version=config.preprocessing.normalization_version,
            query_prefix=config.query_prefix,
            document_prefix=config.document_prefix,
            device=config.device,
            backend=config.backend,
            normalize_embeddings=config.normalize_embeddings,
        )

    @property
    def info(self) -> ModelInfo:
        return self._info

    def embed_query(self, text: str) -> QueryEmbeddingResult:
        prefixed = self._apply_prefix(text, is_query=True)
        started = time.perf_counter()
        try:
            raw = self._model.encode(
                [prefixed],
                batch_size=1,
                convert_to_numpy=True,
                normalize_embeddings=self._config.normalize_embeddings,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingInferenceError(f"Query embedding failed: {exc.__class__.__name__}") from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        vector = self._to_vector(raw[0])
        return QueryEmbeddingResult(vector=vector, model_info=self.info, latency_ms=elapsed_ms)

    def embed_documents(self, texts: Sequence[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(
                vectors=[], model_info=self.info, latency_ms=0.0, batch_size=0
            )
        prefixed = [self._apply_prefix(text, is_query=False) for text in texts]
        started = time.perf_counter()
        vectors: list[Vector] = []
        batch_size = max(1, self._config.batch_size)
        try:
            for start in range(0, len(prefixed), batch_size):
                batch = prefixed[start : start + batch_size]
                encoded = self._model.encode(
                    batch,
                    batch_size=batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=self._config.normalize_embeddings,
                    show_progress_bar=False,
                )
                vectors.extend(self._to_vector(row) for row in encoded)
        except Exception as exc:
            raise EmbeddingInferenceError(
                f"Document embedding failed: {exc.__class__.__name__}"
            ) from exc
        elapsed_ms = (time.perf_counter() - started) * 1000
        return EmbeddingResult(
            vectors=vectors,
            model_info=self.info,
            latency_ms=elapsed_ms,
            batch_size=len(texts),
        )

    def health_check(self) -> bool:
        try:
            result = self.embed_query("probe")
        except EmbeddingInferenceError:
            return False
        return result.vector.shape == (self._dimension,)

    def _apply_prefix(self, text: str, *, is_query: bool) -> str:
        prefix = self._config.query_prefix if is_query else self._config.document_prefix
        if prefix:
            return f"{prefix}{text}"
        return text

    @staticmethod
    def _to_vector(raw: object) -> Vector:
        array = np.asarray(raw, dtype=np.float32)
        if array.ndim != 1:
            raise EmbeddingInferenceError("Expected 1-D embedding vector")
        return array

    @staticmethod
    def _load_model(config: EmbeddingConfig):
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingModelLoadError(
                "sentence-transformers and torch are required for local embedding backends"
            ) from exc

        if config.torch_seed is not None:
            torch.manual_seed(config.torch_seed)

        device = config.device
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise EmbeddingDeviceError(f"CUDA device requested but unavailable: {device}")

        import os
        import concurrent.futures

        # Check candidate local model paths in order of preference
        local_model_path = None
        env_model_path = os.getenv("RAG_EMBEDDING_MODEL_PATH")
        candidate_paths = [
            env_model_path,
            config.model_id,
            r"D:\models\bge-m3",
            "/models/bge-m3",
        ]
        for p in candidate_paths:
            if p and os.path.isdir(p):
                local_model_path = p
                break

        target_model = local_model_path or config.model_id
        is_local_dir = bool(local_model_path)

        def _instantiate():
            if is_local_dir:
                return SentenceTransformer(
                    target_model,
                    device=device,
                    local_files_only=True,
                )
            return SentenceTransformer(
                target_model,
                device=device,
                revision=config.revision,
            )

        # If local directory is present, give enough time for disk load (20s), else strict 6s timeout
        load_timeout = 20.0 if is_local_dir else 6.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_instantiate)
            try:
                model = future.result(timeout=load_timeout)
            except concurrent.futures.TimeoutError:
                raise EmbeddingModelLoadError(
                    f"Loading model {target_model} timed out after {load_timeout}s."
                )
            except Exception as exc:
                raise EmbeddingModelLoadError(
                    f"Failed to load model {target_model}: {exc.__class__.__name__} ({exc})"
                ) from exc

        if config.max_sequence_length is not None:
            model.max_seq_length = config.max_sequence_length
        model.eval()
        return model

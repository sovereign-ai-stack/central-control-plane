"""Sentence-transformers backend — local inference only."""

from __future__ import annotations

import concurrent.futures
import os
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
    def __init__(self, config: EmbeddingConfig) -> None:
        self._config = config
        self._model = self._load_model(config)
        self._dimension = self._discover_dimension()
        max_seq = getattr(self._model, "max_seq_length", None)
        self._max_sequence_length = int(max_seq) if max_seq is not None else 512
        detected_name = getattr(self._model, "_detected_name", None)
        effective_model_id = (
            os.getenv("RAG_EMBEDDING_MODEL_ID")
            or (detected_name if detected_name and detected_name not in ("models", "bge-m3") else None)
            or config.model_id
        )
        self._info = ModelInfo(
            model_id=effective_model_id,
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

    def _discover_dimension(self) -> int:
        """
        Embedding width, asked of the model first and measured if it will not say.

        A sentence-transformers module built from a repo's own `custom_st.py`
        has no Pooling layer to interrogate, so the library reports None. The
        width is still a fact about the loaded model — probe for it rather than
        trusting a configured number.
        """
        reported = None
        for name in ("get_sentence_embedding_dimension", "get_embedding_dimension"):
            getter = getattr(self._model, name, None)
            if getter is None:
                continue
            try:
                reported = getter()
            except Exception:  # noqa: BLE001 - fall through to the probe
                reported = None
            if reported:
                return int(reported)
        try:
            probe = self._model.encode(
                ["probe"],
                batch_size=1,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingModelLoadError(
                f"Could not determine embedding dimension: {exc.__class__.__name__}"
            ) from exc
        return int(np.asarray(probe).reshape(1, -1).shape[1])

    @classmethod
    def _sentence_transformer_kwargs(cls, config: EmbeddingConfig) -> dict:
        """Extra SentenceTransformer constructor kwargs. Empty for stock models."""
        return {}

    @classmethod
    def _post_load(cls, model, config: EmbeddingConfig) -> None:
        """Adjust a freshly loaded model. No-op for stock models."""

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

    @classmethod
    def _find_model_directory(cls, candidate_roots: list[str | None]) -> tuple[str | None, str | None]:
        """
        Smartly discovers an offline model directory among candidate root directories.
        Returns (model_path, detected_name).
        Supports:
        1. A root containing model files directly (config.json, modules.json, weights, etc.)
        2. A root containing subfolder(s) with model files (e.g. /models/any-model-name)
        """
        import os

        def _has_model_files(path: str) -> bool:
            if not os.path.isdir(path):
                return False
            try:
                entries = set(os.listdir(path))
                if "config.json" in entries or "modules.json" in entries or "open_clip_config.json" in entries:
                    return True
                return any(e.endswith(".safetensors") or e.endswith(".bin") for e in entries)
            except OSError:
                return False

        for root in candidate_roots:
            if not root or not os.path.isdir(root):
                continue
            # 1. Check if root directly contains model files
            if _has_model_files(root):
                return root, os.path.basename(os.path.normpath(root))
            # 2. Check all subdirectories inside root
            try:
                subdirs = sorted(
                    [
                        os.path.join(root, d)
                        for d in os.listdir(root)
                        if os.path.isdir(os.path.join(root, d))
                    ]
                )
                for s in subdirs:
                    if _has_model_files(s):
                        return s, os.path.basename(s)
            except OSError:
                continue

        return None, None

    @classmethod
    def _load_model(cls, config: EmbeddingConfig):
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
        env_model_path = os.getenv("RAG_EMBEDDING_MODEL_PATH")
        candidate_roots = [
            env_model_path,
            "/models",
            "/models/bge-m3",
            "../models",
            "./models",
            r"D:\models\bge-m3",
            r"D:\models",
        ]
        local_model_path, detected_name = cls._find_model_directory(candidate_roots)

        target_model = local_model_path or config.model_id
        is_local_dir = bool(local_model_path)

        extra_kwargs = dict(cls._sentence_transformer_kwargs(config))
        if "trust_remote_code" not in extra_kwargs:
            extra_kwargs["trust_remote_code"] = True

        def _instantiate():
            if is_local_dir:
                return SentenceTransformer(
                    target_model,
                    device=device,
                    local_files_only=True,
                    **extra_kwargs,
                )
            return SentenceTransformer(
                target_model,
                device=device,
                revision=config.revision,
                **extra_kwargs,
            )

        # If local directory is present, give enough time for disk load (20s), else strict 6s timeout.
        # Serving wants a fail-fast load; offline work (benchmarks) sets its own
        # budget through config, because a cold multi-hundred-MB checkpoint
        # legitimately takes minutes and must not be silently skipped.
        if config.load_timeout_sec is not None:
            load_timeout = float(config.load_timeout_sec)
        else:
            env_timeout = os.getenv("RAG_EMBEDDING_LOAD_TIMEOUT")
            load_timeout = float(env_timeout) if env_timeout else (60.0 if is_local_dir else 10.0)

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
        if detected_name:
            setattr(model, "_detected_name", detected_name)
        cls._post_load(model, config)
        return model

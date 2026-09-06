"""Embedding subsystem errors."""


class EmbeddingError(Exception):
    """Base embedding error."""


class EmbeddingValidationError(EmbeddingError):
    """Empty text, too long, or invalid input."""


class EmbeddingModelLoadError(EmbeddingError):
    """Model download or load failure."""


class EmbeddingInferenceError(EmbeddingError):
    """OOM or runtime inference failure."""


class EmbeddingDimensionMismatch(EmbeddingError):
    """Vector store dimension does not match model dimension."""


class EmbeddingDeviceError(EmbeddingError):
    """Incompatible or unavailable compute device."""

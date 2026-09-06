"""Secure retrieval errors."""


class RetrievalError(Exception):
    """Base retrieval error."""


class RetrievalValidationError(RetrievalError):
    """Invalid retrieval options or inputs."""


class RetrievalDimensionMismatchError(RetrievalError):
    """Query vector dimension incompatible with stored chunk vectors."""


class RetrievalModelMismatchError(RetrievalError):
    """Query embedding model incompatible with stored chunk vectors."""

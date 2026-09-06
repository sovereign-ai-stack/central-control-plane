"""
Storage backend errors.

These are raised by `ChunkStore` implementations and are deliberately backend
neutral: callers must not have to know whether the store is in-memory or a
vector database. Messages never carry credentials, endpoints, or chunk content.
"""

from __future__ import annotations


class StorageError(Exception):
    """Base storage backend error."""


class StorageConfigurationError(StorageError):
    """Invalid or incomplete vector store configuration."""


class StorageBackendUnavailableError(StorageError):
    """The backend or its client library could not be reached or loaded."""


class StorageWriteError(StorageError):
    """A write failed; the store was left in its prior state."""


class StorageScopeTooLargeError(StorageError):
    """
    The authorized scope cannot be expressed as a single backend filter.

    Raised instead of weakening the filter: failing closed is the only safe
    response, because a dropped scope filter would return unauthorized chunks.
    """

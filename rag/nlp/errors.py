"""Persian NLP layer errors."""

from __future__ import annotations


class NlpError(Exception):
    """Base Persian NLP error."""


class NlpConfigurationError(NlpError):
    """Invalid NLP configuration."""


class NlpBackendUnavailableError(NlpError):
    """A configured optional backend is not installed or failed to load."""

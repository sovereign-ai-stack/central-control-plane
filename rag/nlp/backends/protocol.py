"""
Morphology backend contract and factory.

The rule-based backend is the default and has no dependencies. Third-party
backends are optional adapters selected by name in `config/nlp.yaml`, so the
NLP layer never hard-depends on a library that may not install.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from rag.nlp.errors import NlpBackendUnavailableError, NlpConfigurationError

BACKEND_RULE_BASED = "rule_based"
BACKEND_HAZM = "hazm"
SUPPORTED_BACKENDS = (BACKEND_RULE_BASED, BACKEND_HAZM)


@runtime_checkable
class MorphologyBackend(Protocol):
    @property
    def name(self) -> str:
        ...

    def lemmatize(self, tokens: list[str]) -> list[str]:
        """Return one lemma per input token, preserving order and length."""
        ...


def create_backend(name: str, **kwargs: object) -> MorphologyBackend:
    """
    Build a backend by name.

    Raises NlpBackendUnavailableError (not ImportError) when an optional
    dependency is missing, so callers can fall back deliberately.
    """
    if name == BACKEND_RULE_BASED:
        from rag.nlp.backends.rule_based import RuleBasedMorphologyBackend

        rules = kwargs.get("rules")
        return RuleBasedMorphologyBackend(rules)  # type: ignore[arg-type]
    if name == BACKEND_HAZM:
        from rag.nlp.backends.hazm import HazmMorphologyBackend, hazm_available

        if not hazm_available():
            raise NlpBackendUnavailableError(
                "hazm backend requested but the hazm package is not installed"
            )
        return HazmMorphologyBackend()
    raise NlpConfigurationError(
        f"unsupported morphology backend {name!r}; expected one of {SUPPORTED_BACKENDS}"
    )

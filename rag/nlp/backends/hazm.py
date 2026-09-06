"""
Optional hazm morphology backend.

hazm is **not** a project dependency. It pulls in gensim, which has no wheel for
the Python version this repository targets and fails to build from source, so
requiring it would make the project uninstallable. This adapter exists so that a
deployment which *can* install hazm gets its lemmatizer by setting
`morphology.backend: hazm` in `config/nlp.yaml`, with no other code change.

Everything here is import-guarded; the module is safe to import unconditionally.
"""

from __future__ import annotations

from typing import Any

from rag.nlp.errors import NlpBackendUnavailableError


def hazm_available() -> bool:
    try:
        import hazm  # noqa: F401
    except Exception:  # noqa: BLE001 - any failure means the backend is unusable
        # hazm can fail at import time for reasons beyond ImportError
        # (missing model data, incompatible numpy), all of which mean "unavailable".
        return False
    return True


class HazmMorphologyBackend:
    """Wraps `hazm.Lemmatizer` behind the `MorphologyBackend` contract."""

    def __init__(self, lemmatizer: Any | None = None) -> None:
        self._lemmatizer = lemmatizer if lemmatizer is not None else self._build()

    @staticmethod
    def _build() -> Any:
        try:
            import hazm
        except Exception as exc:
            raise NlpBackendUnavailableError(
                "hazm is not installed; install it or use the rule_based backend"
            ) from exc
        return hazm.Lemmatizer()

    @property
    def name(self) -> str:
        return "hazm"

    def lemmatize(self, tokens: list[str]) -> list[str]:
        lemmas: list[str] = []
        for token in tokens:
            try:
                lemma = self._lemmatizer.lemmatize(token)
            except Exception:  # noqa: BLE001 - fall back to the surface form
                lemma = token
            # hazm returns "present#past" for verbs; keep the first form.
            if isinstance(lemma, str) and "#" in lemma:
                lemma = lemma.split("#", 1)[0]
            lemmas.append(lemma or token)
        return lemmas

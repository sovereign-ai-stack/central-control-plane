"""Default morphology backend — deterministic, dependency-free."""

from __future__ import annotations

from rag.nlp.morphology import MorphologyRules, lemmatize_token


class RuleBasedMorphologyBackend:
    """Suffix-stripping lemmatizer with over-stemming guards."""

    def __init__(self, rules: MorphologyRules | None = None) -> None:
        self._rules = rules or MorphologyRules()

    @property
    def name(self) -> str:
        return "rule_based"

    @property
    def rules(self) -> MorphologyRules:
        return self._rules

    def lemmatize(self, tokens: list[str]) -> list[str]:
        return [lemmatize_token(token, self._rules) for token in tokens]

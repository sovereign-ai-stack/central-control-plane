"""Morphology backends: pure-Python default, optional third-party adapters."""

from rag.nlp.backends.hazm import HazmMorphologyBackend, hazm_available
from rag.nlp.backends.protocol import MorphologyBackend, create_backend
from rag.nlp.backends.rule_based import RuleBasedMorphologyBackend

__all__ = [
    "HazmMorphologyBackend",
    "MorphologyBackend",
    "RuleBasedMorphologyBackend",
    "create_backend",
    "hazm_available",
]

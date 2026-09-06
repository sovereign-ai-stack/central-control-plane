"""
Intent Definitions Package.
Exports specialized intent keyword sets for Coding and Reasoning.
(RAG is explicitly controlled via the Knowledge Base Toggle Switch).
"""

from app.router.intents.coding import CODING_PHRASES, CODING_KEYWORDS
from app.router.intents.reasoning import REASONING_PHRASES, REASONING_KEYWORDS

__all__ = [
    "CODING_PHRASES",
    "CODING_KEYWORDS",
    "REASONING_PHRASES",
    "REASONING_KEYWORDS",
]

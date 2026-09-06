"""
Semantic Router Engine.
Executes multi-tier intent classification combining:
1. User explicit toggle override (Primary control for RAG)
2. High-precision multi-word phrase matching (Coding / Reasoning)
3. Tokenized keyword boundary matching (Coding / Reasoning)
4. Dynamic Semantic Router Service fallback
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.router.normalizer import normalize_text, extract_tokens
from app.router.intents import (
    CODING_PHRASES,
    CODING_KEYWORDS,
    REASONING_PHRASES,
    REASONING_KEYWORDS,
)

logger = logging.getLogger("SemanticRouterEngine")


@dataclass
class RouteClassificationResult:
    route: str  # "rag" | "coding" | "reasoning" | "general"
    method: str  # "explicit_toggle" | "phrase_match" | "keyword_match" | "semantic_service" | "default"
    confidence: float  # 0.0 to 1.0
    matched_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticRouterEngine:
    """Production-grade modular intent classifier."""

    def __init__(self):
        # Pre-normalize all phrases and keywords for ultra-fast matching
        self._normalized_coding_phrases = [normalize_text(p) for p in CODING_PHRASES if p]
        self._normalized_coding_keywords = {normalize_text(k) for k in CODING_KEYWORDS if k}

        self._normalized_reasoning_phrases = [normalize_text(p) for p in REASONING_PHRASES if p]
        self._normalized_reasoning_keywords = {normalize_text(k) for k in REASONING_KEYWORDS if k}

    def _score_intent(
        self,
        normalized_query: str,
        query_tokens: Set[str],
        phrases: List[str],
        keywords: Set[str],
    ) -> Tuple[float, List[str]]:
        """
        Calculates intent score based on:
        - Multi-word exact phrase occurrences (weight 3.0 each)
        - Exact token boundary matches (weight 1.0 each)
        """
        score = 0.0
        matched = []

        # 1. Multi-word phrase matching
        for phrase in phrases:
            if phrase and phrase in normalized_query:
                score += 3.0
                matched.append(f"phrase:{phrase}")

        # 2. Tokenized keyword matching (strict word boundary to avoid false positives like 'کد' in 'کدام')
        for kw in keywords:
            if kw and kw in query_tokens:
                score += 1.0
                matched.append(f"token:{kw}")

        return score, matched

    def classify(
        self,
        query: str,
        explicit_use_rag: Optional[bool] = None,
        semantic_client: Any = None,
        user_id: str = "u_admin",
        session_id: Optional[str] = None,
    ) -> RouteClassificationResult:
        """
        Classifies incoming query into one of the designated routes:
        - 'rag': Enterprise document retrieval & knowledge base (Triggered when explicit_use_rag is True)
        - 'coding': Programming, syntax, debugging, algorithms
        - 'reasoning': Mathematical proof, logic, step-by-step analytical reasoning
        - 'general': Conversational AI assistant
        """
        norm_query = normalize_text(query)
        tokens = extract_tokens(norm_query)

        # -------------------------------------------------------------------
        # Tier 1: User Explicit RAG Toggle Priority
        # -------------------------------------------------------------------
        if explicit_use_rag is True:
            return RouteClassificationResult(
                route="rag",
                method="explicit_user_toggle",
                confidence=1.0,
                matched_patterns=["rag_toggle_enabled"],
            )

        # -------------------------------------------------------------------
        # Tier 2: Keyword & Phrase Matching for Coding vs Reasoning
        # -------------------------------------------------------------------
        coding_score, coding_matches = self._score_intent(
            norm_query, tokens, self._normalized_coding_phrases, self._normalized_coding_keywords
        )
        reasoning_score, reasoning_matches = self._score_intent(
            norm_query, tokens, self._normalized_reasoning_phrases, self._normalized_reasoning_keywords
        )

        if coding_score > 0 and coding_score >= reasoning_score:
            confidence = min(0.99, 0.75 + (coding_score * 0.08))
            method = "phrase_match" if any("phrase:" in m for m in coding_matches) else "keyword_match"
            return RouteClassificationResult(
                route="coding",
                method=method,
                confidence=round(confidence, 3),
                matched_patterns=coding_matches[:5],
            )

        if reasoning_score > 0:
            confidence = min(0.99, 0.75 + (reasoning_score * 0.08))
            method = "phrase_match" if any("phrase:" in m for m in reasoning_matches) else "keyword_match"
            return RouteClassificationResult(
                route="reasoning",
                method=method,
                confidence=round(confidence, 3),
                matched_patterns=reasoning_matches[:5],
            )

        # -------------------------------------------------------------------
        # Tier 3: Semantic Router Service Fallback (if available)
        # -------------------------------------------------------------------
        if semantic_client:
            try:
                semantic_res = semantic_client.chat(
                    query=query,
                    user_id=user_id,
                    session_id=session_id or "default_session",
                )
                if semantic_res and "route" in semantic_res:
                    s_route = semantic_res.get("route", "general")
                    # If semantic service suggested RAG but toggle is not enabled, fallback to general
                    if s_route == "rag" and not explicit_use_rag:
                        s_route = "general"
                    s_conf = float(semantic_res.get("confidence", 0.92))
                    return RouteClassificationResult(
                        route=s_route,
                        method="semantic_router_service",
                        confidence=s_conf,
                        matched_patterns=["semantic_embedding_classifier"],
                        metadata={"raw_response": semantic_res},
                    )
            except Exception as e:
                logger.debug(f"[SemanticRouter] Remote service fallback notice: {e}")

        # -------------------------------------------------------------------
        # Tier 4: General Fallback
        # -------------------------------------------------------------------
        return RouteClassificationResult(
            route="general",
            method="default_general_fallback",
            confidence=0.85,
            matched_patterns=[],
        )


# Global singleton instance
semantic_router_engine = SemanticRouterEngine()

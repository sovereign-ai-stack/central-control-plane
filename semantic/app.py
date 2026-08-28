#!/usr/bin/env python3
"""
Enterprise Semantic Router & Dynamic Request Orchestrator.
Processes incoming user prompts, evaluates intent via sub-millisecond local embeddings,
retrieves enterprise knowledge (RAG) when necessary, and dispatches the request to the optimal LLM.

Reference: https://github.com/vllm-project/semantic-router
"""

import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from routes_config import (
    CODING_KEYWORDS,
    CODING_SAMPLES,
    GENERAL_SAMPLES,
    RAG_KEYWORDS,
    RAG_SAMPLES,
    REASONING_KEYWORDS,
    REASONING_SAMPLES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [SemanticRouter] %(message)s")
logger = logging.getLogger("SemanticRouter")

app = FastAPI(title="Enterprise Semantic Router & LLM Dispatcher", version="2.0.0")

# Service URLs from Environment
RAG_URL = os.environ.get("RAG_URL", "http://host.docker.internal:8100")
LLM_GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://litellm:4000")
LLM_GATEWAY_KEY = os.environ.get("LLM_GATEWAY_KEY", "sk-lite-master-1234")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "qwen-7b")
ENCODER_MODEL_NAME = os.environ.get("ENCODER_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Model routing policy based on classified abstract roles
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "general-model")
ENCODER_MODEL_NAME = os.environ.get("ENCODER_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

ROUTE_MODEL_MAPPING = {
    "general": os.environ.get("ROLE_GENERAL", "general-model"),
    "coding": os.environ.get("ROLE_CODING", "coding-model"),
    "reasoning": os.environ.get("ROLE_REASONING", "reasoning-model"),
    "rag": os.environ.get("ROLE_RAG", "rag-model"),
}


# ------------------------------------------------------------------------------
# 1. Classification Engine (Semantic Router + Hybrid Heuristic Fallback)
# ------------------------------------------------------------------------------
def keyword_score(text: str, keywords: List[str]) -> int:
    t = text.lower()
    return sum(1 for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", t))


def heuristic_classify(text: str) -> Tuple[str, float]:
    """Ultra-fast regex & keyword fallback if embedding model is warming up."""
    rag_s = keyword_score(text, RAG_KEYWORDS)
    code_s = keyword_score(text, CODING_KEYWORDS)
    reas_s = keyword_score(text, REASONING_KEYWORDS)

    scores = [("rag", rag_s), ("coding", code_s), ("reasoning", reas_s)]
    scores.sort(key=lambda x: x[1], reverse=True)
    top_route, top_score = scores[0]

    if top_score > 0:
        conf = round(min(0.60 + 0.08 * top_score, 0.96), 2)
        return top_route, conf
    return "general", 0.50


# Initialize Semantic Router with Local Hugging Face / Sentence-Transformers Encoder
semantic_route_layer = None
try:
    from semantic_router import Route, RouteLayer
    from semantic_router.encoders import HuggingFaceEncoder

    encoder = HuggingFaceEncoder(name=ENCODER_MODEL_NAME)
    routes = [
        Route(name="general", samples=GENERAL_SAMPLES),
        Route(name="coding", samples=CODING_SAMPLES),
        Route(name="reasoning", samples=REASONING_SAMPLES),
        Route(name="rag", samples=RAG_SAMPLES),
    ]
    semantic_route_layer = RouteLayer(encoder=encoder, routes=routes)
    logger.info(f"✅ Semantic Router initialized successfully with encoder: {ENCODER_MODEL_NAME}")
except Exception as e:
    logger.warning(f"⚠️  Embedding encoder unavailable ({e}). Using fast hybrid heuristic fallback.")


def classify_intent(query_text: str) -> Tuple[str, float]:
    """Evaluates query using vector semantic layer with heuristic safety net."""
    if semantic_route_layer is not None:
        try:
            choice = semantic_route_layer(query_text)
            if choice is not None and choice.name:
                conf = getattr(choice, "confidence_score", getattr(choice, "confidence", 0.85)) or 0.85
                return choice.name, round(float(conf), 3)
        except Exception as e:
            logger.debug(f"Semantic layer error on query: {e}")

    return heuristic_classify(query_text)


# ------------------------------------------------------------------------------
# 2. HTTP Helper Utilities
# ------------------------------------------------------------------------------
def raw_http_json(method: str, url: str, body: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 60) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    hdrs = headers or {}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw_err = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw_err)
        except Exception:
            return e.code, {"error": raw_err}
    except Exception as e:
        return 502, {"error": str(e)}


def query_rag_engine(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Fetches relevant document chunks from the RAG Service."""
    url = f"{RAG_URL.rstrip('/')}/retrieve"
    payload = {"query": query, "top_k": top_k}
    status, data = raw_http_json("POST", url, body=payload, timeout=15)
    if status == 200:
        return data.get("results", [])
    logger.warning(f"RAG service returned status {status}: {data}")
    return []


def forward_to_litellm(payload: Dict[str, Any], api_key: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    """Dispatches the chat completion request to LiteLLM Proxy."""
    url = f"{LLM_GATEWAY_URL.rstrip('/')}/v1/chat/completions"
    key_to_use = api_key or LLM_GATEWAY_KEY
    headers = {"Authorization": f"Bearer {key_to_use}"}
    return raw_http_json("POST", url, body=payload, headers=headers, timeout=300)


# ------------------------------------------------------------------------------
# 3. API Request / Response Schemas
# ------------------------------------------------------------------------------
class RouteInspectionRequest(BaseModel):
    query: str = Field(..., description="User prompt to inspect")


class RouteInspectionResponse(BaseModel):
    query: str
    route: str
    confidence: float
    target_model: str
    needs_rag: bool


class ChatCompletionRequest(BaseModel):
    query: str = Field(..., description="User message or prompt")
    model: Optional[str] = Field(None, description="Optional override for model alias")
    max_tokens: int = Field(512, ge=1, le=4096)
    temperature: float = Field(0.3, ge=0.0, le=2.0)
    api_key: Optional[str] = Field(None, description="Client virtual API key")


class ChatCompletionResponse(BaseModel):
    answer: str
    route: str
    confidence: float
    used_rag: bool
    model: str
    usage: Dict[str, Any] = {}
    rag_sources: List[Dict[str, Any]] = []


# ------------------------------------------------------------------------------
# 4. API Endpoints
# ------------------------------------------------------------------------------
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "semantic_engine": "active" if semantic_route_layer is not None else "heuristic_mode",
        "encoder": ENCODER_MODEL_NAME,
        "available_routes": list(ROUTE_MODEL_MAPPING.keys()),
    }


@app.get("/routes")
def list_routes():
    """Lists all configured semantic routes and their target models."""
    return {
        "routes": [
            {
                "name": name,
                "target_model": model,
                "needs_rag": (name == "rag"),
            }
            for name, model in ROUTE_MODEL_MAPPING.items()
        ]
    }


@app.post("/route", response_model=RouteInspectionResponse)
def inspect_route(req: RouteInspectionRequest):
    """Analyzes a query and returns the classified route without calling the LLM."""
    route_name, conf = classify_intent(req.query)
    target_model = ROUTE_MODEL_MAPPING.get(route_name, DEFAULT_MODEL)
    return RouteInspectionResponse(
        query=req.query,
        route=route_name,
        confidence=conf,
        target_model=target_model,
        needs_rag=(route_name == "rag"),
    )


@app.post("/chat", response_model=ChatCompletionResponse)
def handle_chat_query(req: ChatCompletionRequest):
    """
    End-to-end intelligent chat pipeline (Zero-Failure Architecture):
    1. Layer 1 (Semantic Route): Fast intent classification.
    2. Layer 2 (Dynamic RAG Probe): If route is RAG or general/ambiguous, probe the actual
       Vector Knowledge Base. If relevant documents exist, automatically activate RAG!
    3. Ground prompt with retrieved citations and select target model role.
    4. Forward to LiteLLM Proxy (accounting for tokens, budget, and rate limits).
    5. Return structured answer with provenance metadata.
    """
    route_name, conf = classify_intent(req.query)
    rag_chunks = []

    # Dynamic RAG Probe: If route is explicitly RAG OR if it's general/ambiguous,
    # probe the knowledge base to guarantee no company question is ever missed!
    should_probe_rag = (route_name == "rag") or (route_name == "general" and conf < 0.85)

    if should_probe_rag:
        try:
            candidate_chunks = query_rag_engine(req.query, top_k=4)
            # Filter chunks with meaningful relevance score
            valid_chunks = [c for c in candidate_chunks if c.get("score", 1.0) > 0.05]
            if valid_chunks:
                rag_chunks = valid_chunks
                route_name = "rag"
                conf = max(conf, float(valid_chunks[0].get("score", 0.85)))
                logger.info(f"✨ Auto-RAG activated with {len(rag_chunks)} matched document chunks.")
        except Exception as e:
            logger.warning(f"RAG probe error: {e}")

    chosen_model = req.model or ROUTE_MODEL_MAPPING.get(route_name, DEFAULT_MODEL)

    messages = [
        {"role": "system", "content": "شما دستیار هوش مصنوعی سازمان هستید. به سوالات با دقت، ادب و به زبان فارسی پاسخ دهید."}
    ]

    if rag_chunks:
        context_text = "\n\n".join(
            f"[منبع {i+1}]: {c.get('content')} (مرجع: {c.get('metadata', {}).get('source', 'اسناد داخلی')})"
            for i, c in enumerate(rag_chunks)
        )
        messages[0] = {
            "role": "system",
            "content": (
                "شما دستیار سازمانی هستید. صرفاً بر اساس اطلاعات موثق زیر به سوال پاسخ دهید "
                "و در پاسخ خود حتماً به شماره منبع استناد کنید:\n\n" + context_text
            ),
        }
    elif route_name == "rag" and not rag_chunks:
        messages[0] = {
            "role": "system",
            "content": "شما دستیار سازمانی هستید. سند مرتبطی با این سوال در پایگاه دانش یافت نشد. صادقانه اعلام کنید اطلاعاتی در اسناد ثبت نشده است.",
        }

    messages.append({"role": "user", "content": req.query})

    # Forward to LiteLLM
    payload = {
        "model": chosen_model,
        "messages": messages,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
    }

    status, llm_resp = forward_to_litellm(payload, api_key=req.api_key)
    if status != 200:
        error_msg = llm_resp.get("error") or f"LLM Gateway Error (HTTP {status})"
        raise HTTPException(status_code=status, detail=error_msg)

    choice = (llm_resp.get("choices") or [{}])[0].get("message", {})
    answer_text = choice.get("content", "")
    usage_info = llm_resp.get("usage", {})

    return ChatCompletionResponse(
        answer=answer_text,
        route=route_name,
        confidence=conf,
        used_rag=bool(rag_chunks),
        model=chosen_model,
        usage=usage_info,
        rag_sources=rag_chunks,
    )
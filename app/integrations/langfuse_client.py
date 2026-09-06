"""
Langfuse Observability & Pipeline Tracing Integration (Production-Ready for Cloud & Liara).
Provides granular, end-to-end tracing for Semantic Routing, Federated Vector RAG,
LLM Generation, Chain-of-Thought reasoning, Token Quotas, and Error Tracking.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("LangfuseTracer")

# ---------------------------------------------------------------------------
# Production Configuration (Environment Driven for Liara & Docker)
# ---------------------------------------------------------------------------
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY", "pk-lf-8054958d-e8f3-4661-912c-69a351a5156d")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY", "sk-lf-468e625d-5c34-45c6-aca2-a0b24877b3f2")
LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://langfuse:3000")
LANGFUSE_RELEASE = os.environ.get("LANGFUSE_RELEASE", "v2.0.0-production")
LANGFUSE_ENABLED = os.environ.get("LANGFUSE_ENABLED", "true").lower() in ("true", "1", "yes", "on")

_client = None
_client_initialized = False


def get_langfuse_client():
    """
    Singleton client provider with graceful fallback and resilience.
    Does not crash the application if Langfuse is unreachable.
    """
    global _client, _client_initialized
    if not LANGFUSE_ENABLED:
        return None

    if _client_initialized:
        return _client

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
            release=LANGFUSE_RELEASE,
        )
        _client_initialized = True
        logger.info(f"[Langfuse] Initialized production tracer on host: {LANGFUSE_HOST} (release: {LANGFUSE_RELEASE})")
        return _client
    except Exception as e:
        logger.warning(f"[Langfuse] Initialization notice (tracing will be safely bypassed): {e}")
        _client = None
        _client_initialized = True
        return None


class PipelineTrace:
    """
    Production-ready trace manager encapsulating the lifecycle of user interactions.
    Handles high-level traces, intermediate processing spans, LLM generation logs,
    and automatic error reporting.
    """

    def __init__(
        self,
        name: str,
        user_id: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        input_data: Any = None,
    ):
        self.client = get_langfuse_client()
        self.trace = None
        self.start_time = time.time()

        if self.client:
            try:
                self.trace = self.client.trace(
                    name=name,
                    user_id=user_id,
                    session_id=session_id,
                    input=input_data,
                    metadata=metadata or {},
                    tags=tags or [],
                    release=LANGFUSE_RELEASE,
                )
            except Exception as e:
                logger.debug(f"[Langfuse] Trace creation notice: {e}")

    @property
    def id(self) -> Optional[str]:
        """Returns the active Langfuse trace ID if initialized."""
        if self.trace and hasattr(self.trace, "id"):
            return self.trace.id
        return None

    def span(
        self,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "DEFAULT",
        status_message: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ):
        """Records an execution span (e.g. Semantic Routing, Vector Search, Pre-processing)."""
        if not self.trace:
            return None

        try:
            span_kwargs: Dict[str, Any] = {
                "name": name,
                "input": input_data,
                "output": output_data,
                "metadata": metadata or {},
                "level": level,
            }
            if status_message:
                span_kwargs["status_message"] = status_message
            if start_time:
                span_kwargs["start_time"] = start_time
            if end_time:
                span_kwargs["end_time"] = end_time

            active_span = self.trace.span(**span_kwargs)
            active_span.end()
            return active_span
        except Exception as e:
            logger.debug(f"[Langfuse] Span logging notice for '{name}': {e}")
            return None

    def generation(
        self,
        name: str,
        model: str,
        input_data: Any,
        output_data: Any,
        model_parameters: Optional[Dict[str, Any]] = None,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "DEFAULT",
        status_message: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        completion_start_time: Optional[datetime] = None,
    ):
        """
        Records an LLM generation observation with prompt, completion,
        token counts, parameters, and chain-of-thought metadata.
        """
        if not self.trace:
            return None

        try:
            gen_kwargs: Dict[str, Any] = {
                "name": name,
                "model": model,
                "input": input_data,
                "output": output_data,
                "metadata": metadata or {},
                "level": level,
            }
            if model_parameters:
                gen_kwargs["model_parameters"] = model_parameters
            if usage:
                gen_kwargs["usage"] = usage
            if status_message:
                gen_kwargs["status_message"] = status_message
            if start_time:
                gen_kwargs["start_time"] = start_time
            if end_time:
                gen_kwargs["end_time"] = end_time
            if completion_start_time:
                gen_kwargs["completion_start_time"] = completion_start_time

            active_gen = self.trace.generation(**gen_kwargs)
            active_gen.end()
            return active_gen
        except Exception as e:
            logger.debug(f"[Langfuse] Generation logging notice for '{name}': {e}")
            return None

    def event(
        self,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "DEFAULT",
    ):
        """Records a point-in-time milestone event (e.g. Cache Hit, Quota Warning, Fallback Triggered)."""
        if not self.trace:
            return None

        try:
            return self.trace.event(
                name=name,
                input=input_data,
                output=output_data,
                metadata=metadata or {},
                level=level,
            )
        except Exception as e:
            logger.debug(f"[Langfuse] Event logging notice for '{name}': {e}")
            return None

    def record_error(
        self,
        name: str,
        error: Union[Exception, str],
        input_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Records a structured error span with traceback for rapid debugging in Langfuse UI."""
        if not self.trace:
            return None

        err_msg = str(error)
        err_meta = metadata or {}
        err_meta["error_type"] = type(error).__name__ if isinstance(error, Exception) else "GenericError"
        err_meta["traceback"] = traceback.format_exc() if isinstance(error, Exception) else ""

        try:
            span = self.trace.span(
                name=name,
                input=input_data,
                output={"error": err_msg},
                level="ERROR",
                status_message=err_msg,
                metadata=err_meta,
            )
            span.end()
            return span
        except Exception as e:
            logger.debug(f"[Langfuse] Error span logging notice: {e}")
            return None

    def update(
        self,
        input_data: Any = None,
        output_data: Any = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        """Updates the root trace with final output, calculated latencies, and aggregated metadata."""
        if not self.trace:
            return

        try:
            update_kwargs: Dict[str, Any] = {}
            if input_data is not None:
                update_kwargs["input"] = input_data
            if output_data is not None:
                update_kwargs["output"] = output_data
            if metadata is not None:
                update_kwargs["metadata"] = metadata
            if tags is not None:
                update_kwargs["tags"] = tags

            self.trace.update(**update_kwargs)
        except Exception as e:
            logger.debug(f"[Langfuse] Trace update notice: {e}")

    def flush(self):
        """Flushes buffered events to Langfuse server immediately."""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.debug(f"[Langfuse] Flush notice: {e}")


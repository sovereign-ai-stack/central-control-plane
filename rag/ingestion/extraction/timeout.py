"""
Hard wall-clock bound on a single extraction.

Cooperative deadline checks (see `Deadline`) stop a slow document *between*
units of work, which is the common case and actually halts the CPU burn. They
cannot help when one operation hangs — a single PDF page with a pathological
content stream can sit inside the parser indefinitely. This module bounds that.

Honest limitation: Python cannot forcibly kill a thread. On timeout the caller
is released immediately and the request fails, but the orphaned worker keeps
running until the parser returns on its own. Two things bound the damage:

- the cooperative deadline usually ends it at the next page boundary
- the worker is a daemon, so it can never block interpreter shutdown

True CPU reclamation would need process isolation, which costs a process spawn
per upload and is deliberately not done here.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from rag.ingestion.extraction.errors import ExtractionTimeoutError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def run_with_timeout(
    operation: Callable[[], T],
    timeout_seconds: float,
    *,
    description: str = "document extraction",
) -> T:
    """
    Run `operation`, raising `ExtractionTimeoutError` if it outlives the budget.

    A non-positive timeout disables the bound and runs inline, so callers that
    manage their own budget pay nothing for a thread.
    """
    if timeout_seconds <= 0:
        return operation()

    outcome: dict[str, Any] = {}

    def target() -> None:
        try:
            outcome["value"] = operation()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the caller's thread
            outcome["error"] = exc

    worker = threading.Thread(
        target=target, daemon=True, name="rag-extraction"
    )
    worker.start()
    worker.join(timeout_seconds)

    if worker.is_alive():
        logger.warning(
            "%s exceeded %.1fs; abandoning the worker", description, timeout_seconds
        )
        raise ExtractionTimeoutError(
            f"{description} exceeded {timeout_seconds:g} seconds"
        )

    if "error" in outcome:
        # Preserve the original typed error rather than masking it as a timeout.
        raise outcome["error"]
    return outcome["value"]

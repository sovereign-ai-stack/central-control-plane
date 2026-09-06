"""
RAG (Retrieval-Augmented Generation) Subsystem for Sovereign AI Central Control Plane.

Exposes clean Python interfaces for document ingestion, retrieval, reranking, and search.
"""

from rag.service import (
    RAGService,
    rag_service,
    to_uuid,
)

__version__ = "2.0.0"

__all__ = [
    "RAGService",
    "rag_service",
    "to_uuid",
]

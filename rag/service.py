"""
Unified RAG Service for Central Control Plane.

Provides a clean, high-level, production-ready in-process interface
for document ingestion, semantic retrieval, reranking, and context assembly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import uuid
from uuid import UUID

from rag.app.factory import RagApplication
from rag.contracts.retrieval import RetrievalOptions, RetrievalResult, RetrievedChunk
from rag.identity.store import (
    CompanyRecord,
    DepartmentRecord,
    InMemoryIdentityStore,
    UserRecord,
)
from rag.identity.types import TrustedIdentityPayload
from rag.ingestion.authz import IngestPermissionRegistry
from rag.ingestion.types import (
    DocumentStatus,
    IngestDocumentRequest,
    IngestDocumentResponse,
    IngestFileRequest,
)
from rag.pipeline.types import PipelineOptions, RagResult, SourceMetadata

logger = logging.getLogger("CentralRAGService")

_NAMESPACE_RAG = uuid.UUID("1b671a64-40d5-491e-99b0-da01ff1f3341")


def to_uuid(val: Union[str, UUID, None], default_fallback: str = "global") -> UUID:
    """Safely converts string or UUID to a valid UUID object."""
    if val is None:
        return uuid.uuid5(_NAMESPACE_RAG, default_fallback)
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except (ValueError, AttributeError):
        return uuid.uuid5(_NAMESPACE_RAG, str(val))


class RAGService:
    """
    Central in-process RAG Service.
    Wraps the modular RAG application pipeline and exposes a Python API.
    """

    def __init__(
        self,
        app: Optional[RagApplication] = None,
        *,
        auto_register_tenants: bool = True,
    ) -> None:
        self._app: Optional[RagApplication] = app
        self._auto_register = auto_register_tenants
        self._registered_companies: set[UUID] = set()
        self._registered_departments: set[UUID] = set()
        self._registered_users: set[UUID] = set()

    @property
    def app(self) -> RagApplication:
        if self._app is None:
            self._initialize_default_app()
        return self._app  # type: ignore

    def _initialize_default_app(self) -> None:
        """Initializes the RAG application with default settings."""
        import os
        from urllib.parse import urlparse
        identity_store = InMemoryIdentityStore()
        permissions = IngestPermissionRegistry()

        backend = os.getenv("RAG_VECTOR_STORE_BACKEND", "memory").lower()
        if backend == "weaviate":
            try:
                weaviate_url = os.getenv("RAG_WEAVIATE_URL", "http://localhost:18080")
                parsed = urlparse(weaviate_url)
                w_host = parsed.hostname or "localhost"
                w_port = parsed.port or 8080
                w_grpc = int(os.getenv("RAG_WEAVIATE_GRPC_PORT", "50051"))

                from rag.storage.config import VectorStoreConfig, WeaviateConfig
                weav_cfg = WeaviateConfig(
                    host=w_host,
                    http_port=w_port,
                    grpc_port=w_grpc,
                    collection="RagChunk",
                    auto_create_collection=True,
                    auto_create_tenants=True,
                )
                vector_cfg = VectorStoreConfig(
                    backend="weaviate",
                    weaviate=weav_cfg,
                )
                self._app = RagApplication.build_in_memory(
                    identity_store,
                    ingest_permissions=permissions,
                    vector_store_config=vector_cfg,
                )
                logger.info(f"RAGService initialized with persistent Weaviate backend at {w_host}:{w_port}.")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize Weaviate backend ({e}); falling back to in-memory store.")

        self._app = RagApplication.build_in_memory(
            identity_store,
            ingest_permissions=permissions,
        )
        logger.info("RAGService initialized with default in-memory application context.")

    def ensure_department(self, company_uuid: UUID, department_uuid: UUID) -> None:
        """Ensures a department is registered with its company."""
        dept = self.app.identity_store.get_department(department_uuid)
        if dept is None:
            self.app.identity_store.register_department(
                DepartmentRecord(id=department_uuid, company_id=company_uuid)
            )
            self._registered_departments.add(department_uuid)

    def ensure_tenant(
        self,
        organization_id: Union[str, UUID, None],
        team_id: Union[str, UUID, None] = "global",
        user_id: Union[str, UUID, None] = "u_default",
    ) -> tuple[UUID, UUID, UUID]:
        """
        Ensures company, department, and user entities exist in the RAG identity store.
        Grants company-wide ingest permissions to the user for seamless backend operations.
        """
        company_uuid = to_uuid(organization_id, "default_org")

        if isinstance(team_id, UUID):
            department_uuid = team_id
        else:
            department_uuid = to_uuid(f"{company_uuid}:{team_id or 'global'}")

        if isinstance(user_id, UUID):
            user_uuid = user_id
        else:
            user_uuid = to_uuid(f"{company_uuid}:{user_id or 'u_default'}")

        identity_store = self.app.identity_store

        if identity_store.get_company(company_uuid) is None:
            identity_store.register_company(CompanyRecord(id=company_uuid))
            self._registered_companies.add(company_uuid)

        self.ensure_department(company_uuid, department_uuid)

        global_uuid = to_uuid(f"{company_uuid}:global")
        self.ensure_department(company_uuid, global_uuid)

        if identity_store.get_user(user_uuid) is None:
            identity_store.register_user(
                UserRecord(id=user_uuid, company_id=company_uuid),
                department_ids=(department_uuid, global_uuid) if department_uuid != global_uuid else (global_uuid,),
            )
            if hasattr(self.app, "ingestion_service") and hasattr(
                self.app.ingestion_service, "_authz"
            ):
                perm_reg = self.app.ingestion_service._authz._permissions
                if isinstance(perm_reg, IngestPermissionRegistry):
                    perm_reg.grant_company_wide(user_uuid)
            self._registered_users.add(user_uuid)

        return company_uuid, department_uuid, user_uuid

    def ingest_document(
        self,
        content: str,
        organization_id: Union[str, UUID, None] = None,
        team_id: Union[str, UUID, None] = "global",
        *,
        title: Optional[str] = None,
        source: str = "direct_input",
        document_id: Union[str, UUID, None] = None,
        user_id: Union[str, UUID, None] = "u_admin",
        language: str = "fa",
        deduplicate: bool = True,
    ) -> Dict[str, Any]:
        """
        Ingests a plain-text document into the RAG subsystem.
        Chunks, embeds, and indexes the document into the vector store.
        """
        comp_id, dept_id, u_id = self.ensure_tenant(organization_id, team_id, user_id)
        doc_uuid = to_uuid(document_id, str(uuid.uuid4())) if document_id else uuid.uuid4()
        req_id = uuid.uuid4()

        token = f"tok_{u_id.hex[:12]}"
        self.app.identity_store.register_token(
            token_id=uuid.uuid4(),
            user_id=u_id,
            raw_token=token,
        )

        request = IngestDocumentRequest(
            content=content,
            company_id=comp_id,
            department_id=dept_id,
            source=source,
            title=title or source,
            document_id=doc_uuid,
            language=language,
            deduplicate=deduplicate,
        )

        resp = self.app.ingestion_service.create_document(
            request=request,
            request_id=req_id,
            bearer_token=token,
        )

        return {
            "document_id": str(resp.document_id),
            "status": resp.status.value if hasattr(resp.status, "value") else str(resp.status),
            "version": resp.version,
            "chunk_count": resp.chunk_count,
            "content_hash": resp.content_hash,
            "deduplicated": resp.deduplicated,
            "http_status": resp.http_status,
        }

    def ingest_file(
        self,
        data: bytes,
        filename: str,
        organization_id: Union[str, UUID, None] = None,
        team_id: Union[str, UUID, None] = "global",
        *,
        title: Optional[str] = None,
        source: Optional[str] = None,
        document_id: Union[str, UUID, None] = None,
        user_id: Union[str, UUID, None] = "u_admin",
        language: str = "fa",
        deduplicate: bool = True,
    ) -> Dict[str, Any]:
        """
        Ingests a binary file (PDF, TXT, etc.) into the RAG subsystem.
        Extracts content using registered extractors, normalizes Persian text,
        chunks, generates vector embeddings, and indexes chunks.
        """
        comp_id, dept_id, u_id = self.ensure_tenant(organization_id, team_id, user_id)
        doc_uuid = to_uuid(document_id, str(uuid.uuid4())) if document_id else uuid.uuid4()
        req_id = uuid.uuid4()

        token = f"tok_{u_id.hex[:12]}"
        self.app.identity_store.register_token(
            token_id=uuid.uuid4(),
            user_id=u_id,
            raw_token=token,
        )

        file_req = IngestFileRequest(
            data=data,
            filename=filename,
            company_id=comp_id,
            department_id=dept_id,
            source=source or filename,
            title=title or filename,
            document_id=doc_uuid,
            language=language,
            deduplicate=deduplicate,
        )

        resp = self.app.ingestion_service.create_document_from_file(
            request=file_req,
            request_id=req_id,
            bearer_token=token,
        )

        return {
            "document_id": str(resp.document_id),
            "status": resp.status.value if hasattr(resp.status, "value") else str(resp.status),
            "version": resp.version,
            "chunk_count": resp.chunk_count,
            "content_hash": resp.content_hash,
            "deduplicated": resp.deduplicated,
            "http_status": resp.http_status,
        }

    def delete_document(
        self,
        document_id: Union[str, UUID],
        organization_id: Union[str, UUID, None] = None,
        team_id: Union[str, UUID, None] = "global",
        user_id: Union[str, UUID, None] = "u_admin",
    ) -> bool:
        """
        Deletes a document and all its indexed chunks from the RAG store.
        """
        comp_id, dept_id, u_id = self.ensure_tenant(organization_id, team_id, user_id)
        doc_uuid = to_uuid(document_id)
        req_id = uuid.uuid4()

        token = f"tok_{u_id.hex[:12]}"
        self.app.identity_store.register_token(
            token_id=uuid.uuid4(),
            user_id=u_id,
            raw_token=token,
        )

        try:
            self.app.ingestion_service.delete_document(
                document_id=doc_uuid,
                request_id=req_id,
                bearer_token=token,
            )
            return True
        except Exception as e:
            logger.warning(f"Error deleting document {document_id} from RAG: {e}")
            try:
                self.app.chunk_store.delete_by_document_id(doc_uuid)
                return True
            except Exception:
                return False

    def retrieve(
        self,
        query: str,
        organization_id: Union[str, UUID, None] = None,
        team_id: Union[str, UUID, None] = None,
        allowed_team_ids: Optional[Sequence[Union[str, UUID]]] = None,
        user_id: Union[str, UUID, None] = "u_default",
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k relevant chunks for a user query respecting multi-tenant isolation.
        """
        if not query or not query.strip():
            return []

        comp_id, dept_id, u_id = self.ensure_tenant(
            organization_id, team_id or "global", user_id
        )

        dept_uuids = [dept_id]
        self.ensure_department(comp_id, dept_id)

        if allowed_team_ids:
            for t in allowed_team_ids:
                d_u = t if isinstance(t, UUID) else to_uuid(f"{comp_id}:{t}")
                self.ensure_department(comp_id, d_u)
                if d_u not in dept_uuids:
                    dept_uuids.append(d_u)

        global_uuid = to_uuid(f"{comp_id}:global")
        self.ensure_department(comp_id, global_uuid)
        if global_uuid not in dept_uuids:
            dept_uuids.append(global_uuid)

        self.app.identity_store.user_departments[u_id] = tuple(dept_uuids)

        trusted_identity = TrustedIdentityPayload(
            user_id=u_id,
            company_id=comp_id,
            department_ids=tuple(dept_uuids),
        )

        options = RetrievalOptions(top_k=top_k, candidate_k=max(top_k * 2, 8))
        req_id = uuid.uuid4()

        retrieval_result = self.app.retrieval_service.search(
            query=query,
            request_id=req_id,
            trusted_identity=trusted_identity,
            options=options,
        )

        formatted_chunks = []
        for chunk in retrieval_result.chunks:
            if not isinstance(chunk, RetrievedChunk):
                continue
            
            doc_rec = None
            if hasattr(self.app, "document_store") and self.app.document_store:
                doc_rec = self.app.document_store.get(chunk.document_id)
            
            doc_title = (doc_rec.title if doc_rec and doc_rec.title else None) or (doc_rec.source if doc_rec else "")
            doc_source = (doc_rec.source if doc_rec and doc_rec.source else "") or doc_title
            
            formatted_chunks.append({
                "chunk_id": str(chunk.chunk_id),
                "document_id": str(chunk.document_id),
                "content": chunk.content,
                "score": float(chunk.score),
                "source": doc_source,
                "title": doc_title or "سند سازمانی",
                "page": chunk.chunk_index + 1,
                "section": f"بخش {chunk.chunk_index + 1}",
                "company_id": str(chunk.company_id),
                "department_id": str(chunk.department_id),
                "metadata": {
                    "source": doc_source,
                    "title": doc_title or "سند سازمانی",
                    "page": chunk.chunk_index + 1,
                    "section": f"بخش {chunk.chunk_index + 1}",
                },
            })

        return formatted_chunks

    def query(
        self,
        query: str,
        organization_id: Union[str, UUID, None] = None,
        team_id: Union[str, UUID, None] = None,
        allowed_team_ids: Optional[Sequence[Union[str, UUID]]] = None,
        user_id: Union[str, UUID, None] = "u_default",
        top_k: int = 4,
        max_context_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Executes full end-to-end RAG pipeline:
        Retrieve -> Rerank & Diversity -> Deduplicate -> Assemble Context & Citations.
        """
        if not query or not query.strip():
            return {"context": "", "citations": [], "chunks": []}

        comp_id, dept_id, u_id = self.ensure_tenant(
            organization_id, team_id or "global", user_id
        )

        dept_uuids = [dept_id]
        self.ensure_department(comp_id, dept_id)

        if allowed_team_ids:
            for t in allowed_team_ids:
                d_u = t if isinstance(t, UUID) else to_uuid(f"{comp_id}:{t}")
                self.ensure_department(comp_id, d_u)
                if d_u not in dept_uuids:
                    dept_uuids.append(d_u)

        global_uuid = to_uuid(f"{comp_id}:global")
        self.ensure_department(comp_id, global_uuid)
        if global_uuid not in dept_uuids:
            dept_uuids.append(global_uuid)

        self.app.identity_store.user_departments[u_id] = tuple(dept_uuids)

        trusted_identity = TrustedIdentityPayload(
            user_id=u_id,
            company_id=comp_id,
            department_ids=tuple(dept_uuids),
        )

        req_id = uuid.uuid4()
        pipeline_opts = PipelineOptions(
            top_k=top_k,
            max_context_tokens=max_context_tokens,
        )

        rag_result: RagResult = self.app.rag_orchestrator.execute(
            query=query,
            request_id=req_id,
            trusted_identity=trusted_identity,
            options=pipeline_opts,
        )

        formatted_citations = []
        formatted_chunks = []
        for idx, chunk in enumerate(rag_result.chunks):
            doc_rec = None
            if hasattr(self.app, "document_store") and self.app.document_store:
                doc_rec = self.app.document_store.get(chunk.document_id)
            doc_title = (doc_rec.title if doc_rec and doc_rec.title else None) or (doc_rec.source if doc_rec else "") or "سند سازمانی"
            doc_source = (doc_rec.source if doc_rec and doc_rec.source else "") or doc_title

            formatted_citations.append({
                "claimIndex": idx,
                "title": doc_title,
                "section": f"بخش {chunk.chunk_index + 1}",
                "snippet": (chunk.content[:350] + "...") if len(chunk.content) > 350 else chunk.content,
                "url": "/admin#knowledge",
                "supportStatus": "supported",
                "confidenceScore": float(chunk.retrieval_score) if chunk.retrieval_score else None,
            })

            formatted_chunks.append({
                "chunk_id": str(chunk.chunk_id),
                "document_id": str(chunk.document_id),
                "content": chunk.content,
                "score": float(chunk.retrieval_score),
                "metadata": {
                    "source": doc_source,
                    "title": doc_title,
                    "page": chunk.chunk_index + 1,
                    "section": f"بخش {chunk.chunk_index + 1}",
                },
            })

        return {
            "context": rag_result.context.text if rag_result.context else "",
            "citations": formatted_citations,
            "chunks": formatted_chunks,
            "provenance": {
                "chunk_count": len(rag_result.chunks),
                "token_count": rag_result.context.token_count if rag_result.context else 0,
                "latency_ms": rag_result.retrieval.latency_ms if rag_result.retrieval else 0,
            },
        }

    def health(self) -> Dict[str, Any]:
        """Returns health diagnostics of all RAG subsystems."""
        if hasattr(self.app, "health_service"):
            readiness = self.app.health_service.readiness()
            return readiness.to_dict()
        return {"status": "ok"}


rag_service = RAGService()

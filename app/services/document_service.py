"""
Document business logic service for RAG knowledge base.
"""

import io
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.document import DocumentModel
from app.models.organization import OrganizationModel
from app.models.team import TeamModel
from app.services.document_ingestion import process_document_ingestion_task
from rag import rag_service, to_uuid

# Bounded thread pool for background document parsing and embedding
ingestion_executor = ThreadPoolExecutor(
    max_workers=int(os.getenv("INGESTION_WORKERS", "4")),
    thread_name_prefix="doc_ingest",
)


class DocumentService:
    @staticmethod
    def list_documents(
        caller: Dict[str, Any],
        organization_id: Optional[str],
        team_id: Optional[str],
        db: Session,
    ) -> List[Dict[str, Any]]:
        role = caller.get("role")
        caller_org = caller.get("organizationId")
        caller_team = caller.get("teamId")

        query = db.query(DocumentModel)
        if role == "super_admin":
            if organization_id:
                query = query.filter(DocumentModel.organization_id == organization_id)
            if team_id:
                query = query.filter(DocumentModel.team_id == team_id)
        elif role == "org_admin":
            query = query.filter(DocumentModel.organization_id == caller_org)
            if team_id:
                query = query.filter(DocumentModel.team_id == team_id)
        else:
            query = query.filter(
                DocumentModel.organization_id == caller_org,
                DocumentModel.team_id.in_([caller_team, "global"]),
            )

        docs = query.order_by(DocumentModel.created_at.desc()).all()
        res = []
        for d in docs:
            org = db.query(OrganizationModel).filter(OrganizationModel.id == d.organization_id).first()
            team = db.query(TeamModel).filter(TeamModel.id == d.team_id).first()
            org_display = org.name if org else ("سازمان عمومی (کل سامانه)" if d.organization_id in ["", "global", "org_global", None] else d.organization_id)
            team_display = team.name if team else ("پایگاه سراسری (تمام تیم‌ها)" if d.team_id in ["", "global", None] else d.team_id)
            res.append(d.to_dict(org_name=org_display, team_name=team_display))
        return res

    @staticmethod
    def upload_document_sync(
        content: bytes,
        filename: str,
        content_type: str,
        organization_id: Optional[str],
        team_id: Optional[str],
        caller: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        caller_role = caller.get("role")
        caller_org = caller.get("organizationId")
        caller_team = caller.get("teamId")

        # RBAC Enforcement:
        # - super_admin: Can upload to any org/team or 'global' (system-wide public).
        # - org_admin: Can only upload to their own organization (either team='global' for org-wide or a specific team).
        # - team_admin / user: Can only upload to their own team.
        if caller_role == "super_admin":
            target_org = organization_id if organization_id else "global"
            target_team = team_id if team_id else "global"
        elif caller_role == "org_admin":
            target_org = caller_org or "global"
            target_team = team_id if team_id else "global"
        else:
            target_org = caller_org or "global"
            target_team = caller_team or "global"

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Fast estimated page count
        estimated_pages = max(1, len(content) // 40000 + 1)

        # Create record immediately with status='processing' so UI is never blocked
        new_doc = DocumentModel(
            id=doc_id,
            name=filename,
            size=len(content),
            page_count=estimated_pages,
            content_type=content_type,
            organization_id=target_org,
            team_id=target_team,
            chunk_count=0,
            status="processing",
            extracted_text="",
            uploaded_by=caller.get("name", "مدیر سیستم"),
            created_at=now,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # Submit background task to bounded worker pool for PDF parsing & vector embedding
        ingestion_executor.submit(
            process_document_ingestion_task,
            doc_id=doc_id,
            content=content,
            filename=filename,
            content_type=content_type,
            target_org=target_org,
            target_team=target_team,
            caller_id=caller.get("id", "u_admin"),
        )

        org = db.query(OrganizationModel).filter(OrganizationModel.id == target_org).first()
        team = db.query(TeamModel).filter(TeamModel.id == target_team).first()
        org_display = org.name if org else ("سازمان عمومی (کل سامانه)" if target_org in ["", "global", "org_global", None] else target_org)
        team_display = team.name if team else ("پایگاه سراسری (تمام تیم‌ها)" if target_team in ["", "global", None] else target_team)
        return new_doc.to_dict(org_name=org_display, team_name=team_display)

    @staticmethod
    async def upload_document(
        file: UploadFile,
        organization_id: Optional[str],
        team_id: Optional[str],
        caller: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        import asyncio
        content = await file.read()
        return await asyncio.to_thread(
            DocumentService.upload_document_sync,
            content=content,
            filename=file.filename or "uploaded_document.pdf",
            content_type=file.content_type or "application/pdf",
            organization_id=organization_id,
            team_id=team_id,
            caller=caller,
            db=db,
        )

    @staticmethod
    def create_text_document_sync(
        title: str,
        text_content: str,
        organization_id: Optional[str],
        team_id: Optional[str],
        caller: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        caller_role = caller.get("role")
        caller_org = caller.get("organizationId")
        caller_team = caller.get("teamId")

        if caller_role == "super_admin":
            target_org = organization_id if organization_id else "global"
            target_team = team_id if team_id else "global"
        elif caller_role == "org_admin":
            target_org = caller_org or "global"
            target_team = team_id if team_id else "global"
        else:
            target_org = caller_org or "global"
            target_team = caller_team or "global"

        clean_title = (title or "سند متنی").strip()
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        content_bytes = text_content.encode("utf-8")
        estimated_pages = max(1, len(text_content) // 2000 + 1)

        new_doc = DocumentModel(
            id=doc_id,
            name=clean_title,
            size=len(content_bytes),
            page_count=estimated_pages,
            content_type="text/plain",
            organization_id=target_org,
            team_id=target_team,
            chunk_count=0,
            status="processing",
            extracted_text=text_content,
            uploaded_by=caller.get("name", "مدیر سیستم"),
            created_at=now,
        )
        db.add(new_doc)
        db.commit()
        db.refresh(new_doc)

        # Submit background task to bounded worker pool
        ingestion_executor.submit(
            process_document_ingestion_task,
            doc_id=doc_id,
            content=content_bytes,
            filename=f"{clean_title}.txt",
            content_type="text/plain",
            target_org=target_org,
            target_team=target_team,
            caller_id=caller.get("id", "u_admin"),
        )

        org = db.query(OrganizationModel).filter(OrganizationModel.id == target_org).first()
        team = db.query(TeamModel).filter(TeamModel.id == target_team).first()
        org_display = org.name if org else ("سازمان عمومی (کل سامانه)" if target_org in ["", "global", "org_global", None] else target_org)
        team_display = team.name if team else ("پایگاه سراسری (تمام تیم‌ها)" if target_team in ["", "global", None] else target_team)
        return new_doc.to_dict(org_name=org_display, team_name=team_display)

    @staticmethod
    async def create_text_document(
        title: str,
        text_content: str,
        organization_id: Optional[str],
        team_id: Optional[str],
        caller: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        import asyncio
        return await asyncio.to_thread(
            DocumentService.create_text_document_sync,
            title=title,
            text_content=text_content,
            organization_id=organization_id,
            team_id=team_id,
            caller=caller,
            db=db,
        )

    @staticmethod
    def delete_document(doc_id: str, caller: Dict[str, Any], db: Session) -> Dict[str, Any]:
        try:
            doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            if doc:
                # Delete from internal RAG subsystem safely
                try:
                    rag_service.delete_document(
                        document_id=doc_id,
                        organization_id=doc.organization_id,
                        team_id=doc.team_id,
                        user_id=caller.get("id", "u_admin"),
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete document {doc_id} from RAG index: {e}")

                db.delete(doc)
                db.commit()
        except Exception as e:
            logger.error(f"Error during document deletion from DB: {e}")
            db.rollback()
        return {"deleted": True, "id": doc_id}

    @staticmethod
    def ensure_all_documents_indexed(db: Session) -> int:
        """
        Re-hydrates and indexes all persistent documents from PostgreSQL
        into the in-process RAG vector index upon gateway startup.
        """
        try:
            docs = (
                db.query(DocumentModel)
                .filter(
                    DocumentModel.extracted_text != "",
                    DocumentModel.extracted_text != None,
                )
                .all()
            )
            count = 0
            for doc in docs:
                try:
                    # Check if chunks for this document already exist in Weaviate vector store
                    doc_uuid = to_uuid(doc.id)
                    existing_chunks_count = 0
                    try:
                        existing_chunks_count = rag_service.app.chunk_store.count_by_document_id(doc_uuid)
                    except Exception as ce:
                        logger.debug(f"Chunk store count check returned: {ce}")

                    if existing_chunks_count > 0:
                        logger.info(f"⚡ Document {doc.id} ({doc.name}) already has {existing_chunks_count} chunks in Weaviate. Skipping re-embedding.")
                        count += 1
                        continue

                    res = rag_service.ingest_document(
                        content=doc.extracted_text,
                        organization_id=doc.organization_id,
                        team_id=doc.team_id or "global",
                        title=doc.name,
                        source=doc.name,
                        document_id=doc.id,
                        user_id="u_admin",
                        deduplicate=True,
                    )
                    if res and res.get("chunk_count"):
                        count += 1
                except Exception as e:
                    logger.warning(f"Error re-indexing document {doc.id} ({doc.name}): {e}")
            logger.info(f"📚 RAG re-hydration completed: {count}/{len(docs)} documents loaded into vector store.")
            return count
        except Exception as e:
            logger.error(f"Error during RAG re-hydration: {e}")
            return 0


document_service = DocumentService()

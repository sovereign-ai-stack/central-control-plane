import pytest
import io
from app.models.document import DocumentModel
from app.services.document_service import document_service
from rag import rag_service
from tests.conftest import TestingSessionLocal


def test_file_upload_db_delete_orphan_free():
    db = TestingSessionLocal()
    caller = {"id": "u_admin", "name": "مدیر سیستم", "role": "super_admin"}
    
    # 1. Create a markdown text document
    doc_content = "# مستند فنی پایگاه دانش سازمانی\n\nاین یک متن تستی برای بررسی چرخه حیات کامل سند است."
    doc_res = document_service.create_text_document_sync(
        title="سند چرخه حیات",
        text_content=doc_content,
        organization_id="org_lifecycle",
        team_id="team_lifecycle",
        caller=caller,
        db=db,
    )
    doc_id = doc_res["id"]
    
    # Verify Document exists in DB with extracted_text
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    assert doc is not None
    assert doc.name == "سند چرخه حیات"
    assert doc.organization_id == "org_lifecycle"
    assert doc.extracted_text == doc_content
    
    # Manually trigger RAG ingestion to test vector indexing
    rag_res = rag_service.ingest_document(
        content=doc_content,
        organization_id="org_lifecycle",
        team_id="team_lifecycle",
        title=doc.name,
        source=doc.name,
        document_id=doc_id,
        user_id="u_admin",
    )
    assert rag_res["chunk_count"] >= 1
    
    # Verify retrieval finds it
    retrieved = rag_service.retrieve(
        query="چرخه حیات کامل",
        organization_id="org_lifecycle",
        team_id="team_lifecycle",
    )
    assert len(retrieved) > 0
    assert any("چرخه حیات" in r["content"] for r in retrieved)
    
    # 2. Delete Document
    del_res = document_service.delete_document(doc_id=doc_id, caller=caller, db=db)
    assert del_res["deleted"] is True
    
    # 3. Verify PostgreSQL / SQLite database record is completely gone
    db_after = TestingSessionLocal()
    deleted_doc = db_after.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    assert deleted_doc is None, "Document record must be completely deleted from DB (no orphan records)"
    
    # 4. Verify RAG chunks for this doc_id are completely removed
    retrieved_after = rag_service.retrieve(
        query="چرخه حیات کامل",
        organization_id="org_lifecycle",
        team_id="team_lifecycle",
    )
    assert len(retrieved_after) == 0, "No vector chunks should remain in RAG index after deletion"
    db_after.close()
    db.close()

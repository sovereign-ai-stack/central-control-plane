import pytest
from rag import rag_service
from rag.ingestion.extraction.registry import ExtractorRegistry
from app.services.document_ingestion import process_document_ingestion_task
from app.models.document import DocumentModel
from tests.conftest import TestingSessionLocal
from datetime import datetime, timezone


def test_markdown_extractor_registration():
    registry = ExtractorRegistry()
    md_content = b"# Header 1\n\nThis is a **Markdown** document test."
    extractor = registry.select(md_content, filename="guide.md")
    assert extractor is not None
    
    extracted = registry.extract(md_content, filename="guide.md")
    assert "Markdown" in extracted.text
    assert extracted.segments is not None
    assert len(extracted.segments) >= 1


def test_markdown_full_ingestion_and_rag_query():
    db = TestingSessionLocal()
    doc_id = "doc_md_test_1"
    now = datetime.now(timezone.utc).isoformat()
    
    md_bytes = """# راهنمای استفاده از سامانه سازمانی Sovereign

## بخش اول: معماری کلاستر
سامانه Sovereign از معماری ترکیبی میکروسرویس و مدل‌های هوش مصنوعی توزیع‌شده استفاده می‌کند.

## بخش دوم: پروتکل‌های امنیتی
تمام ارتباطات شبکه از طریق TLS 1.3 و توکن‌های نشست رمزنگاری‌شده محافظت می‌شوند.
""".encode("utf-8")

    # Create document record
    doc = DocumentModel(
        id=doc_id,
        name="guide.md",
        size=len(md_bytes),
        page_count=1,
        content_type="text/markdown",
        organization_id="org_md_test",
        team_id="team_md_test",
        chunk_count=0,
        status="processing",
        extracted_text="",
        uploaded_by="مدیر سیستم",
        created_at=now,
    )
    db.add(doc)
    db.commit()

    # Process ingestion task synchronously
    process_document_ingestion_task(
        doc_id=doc_id,
        content=md_bytes,
        filename="guide.md",
        content_type="text/markdown",
        target_org="org_md_test",
        target_team="team_md_test",
        caller_id="u_admin",
        db_session=db,
    )

    # Verify DB record updated
    db = TestingSessionLocal()
    doc_updated = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    assert doc_updated.status == "indexed"
    assert doc_updated.chunk_count >= 1
    assert "معماری ترکیبی میکروسرویس" in doc_updated.extracted_text

    # Verify RAG retrieve returns content
    results = rag_service.retrieve(
        query="پروتکل‌های امنیتی سامانه Sovereign",
        organization_id="org_md_test",
        team_id="team_md_test",
    )
    assert len(results) > 0
    assert any("TLS 1.3" in r["content"] for r in results)
    db.close()

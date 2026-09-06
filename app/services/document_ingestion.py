"""
Background Ingestion Worker for Enterprise Knowledge Base (RAG).
Modular worker running in isolated background threads for high-throughput async processing.
"""

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Optional
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.document import DocumentModel
from rag import rag_service


def extract_docx_text(content: bytes) -> str:
    """Extracts clean text and paragraphs from a Microsoft Word .docx binary."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in tree.iterfind(".//w:p", namespaces):
                texts = [node.text for node in p.iterfind(".//w:t", namespaces) if node.text]
                if texts:
                    paragraphs.append("".join(texts))
            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.warning(f"DOCX XML extraction notice: {e}")
        return extract_plain_text(content)


def extract_plain_text(content: bytes) -> str:
    """Decodes plain text with multiple encoding fallbacks."""
    for enc in ["utf-8", "utf-8-sig", "windows-1256", "cp1256", "iso-8859-1"]:
        try:
            return content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return content.decode("utf-8", errors="replace")


def process_document_ingestion_task(
    doc_id: str,
    content: bytes,
    filename: str,
    content_type: str,
    target_org: str,
    target_team: str,
    caller_id: str,
    db_session: Optional[SessionLocal] = None,
) -> None:
    """
    Background worker function to extract text, compute chunks, generate embeddings,
    and persist results to the database asynchronously.
    Supports PDF, Word (.docx), Markdown (.md), and plain text (.txt).
    """
    logger.info(f"🚀 Starting background ingestion for document '{filename}' (ID: {doc_id}, size: {len(content)} bytes)...")
    owns_session = db_session is None
    db = db_session or SessionLocal()
    try:
        extracted_text = ""
        page_count = 1
        lower_name = filename.lower()

        # 1. Multi-Format Text Extraction
        if lower_name.endswith(".docx") or "wordprocessingml" in content_type.lower():
            extracted_text = extract_docx_text(content)
            page_count = max(1, len(extracted_text) // 2000 + 1)
        elif lower_name.endswith((".txt", ".md", ".markdown", ".json", ".csv")) or "text" in content_type.lower() or "markdown" in content_type.lower():
            extracted_text = extract_plain_text(content)
            page_count = max(1, len(extracted_text) // 2000 + 1)
        elif lower_name.endswith(".pdf") or "pdf" in content_type.lower():
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
                page_count = max(1, len(reader.pages))
                extracted_pages = []
                for i, p in enumerate(reader.pages):
                    txt = p.extract_text() or ""
                    if txt.strip():
                        extracted_pages.append(f"--- [صفحه {i+1}] ---\n{txt}")
                extracted_text = "\n\n".join(extracted_pages)
            except Exception as e:
                logger.warning(f"pypdf extraction notice for {filename}: {e}")
                extracted_text = extract_plain_text(content)
                page_count = max(1, len(content) // 40000 + 1)
        else:
            extracted_text = extract_plain_text(content)
            page_count = max(1, len(content) // 40000 + 1)

        chunk_count = max(1, page_count * 2)

        # 2. Vector Store Ingestion (In-Process RAG)
        try:
            rag_res = rag_service.ingest_file(
                data=content,
                filename=filename,
                organization_id=target_org,
                team_id=target_team,
                title=filename,
                source=filename,
                document_id=doc_id,
                user_id=caller_id,
            )
            if rag_res and "chunk_count" in rag_res:
                chunk_count = rag_res["chunk_count"]
                logger.info(f"✅ Indexed {doc_id} with {chunk_count} chunks into RAG store.")
        except Exception as e:
            logger.warning(f"RAG file ingestion fallback for {doc_id}: {e}")
            if extracted_text.strip():
                try:
                    rag_res = rag_service.ingest_document(
                        content=extracted_text,
                        organization_id=target_org,
                        team_id=target_team,
                        title=filename,
                        source=filename,
                        document_id=doc_id,
                        user_id=caller_id,
                    )
                    if rag_res and "chunk_count" in rag_res:
                        chunk_count = rag_res["chunk_count"]
                except Exception as e2:
                    logger.error(f"Failed fallback RAG ingestion for {doc_id}: {e2}")

        # 3. Update Document Record to 'indexed'
        doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
        if doc:
            doc.page_count = page_count
            doc.chunk_count = chunk_count
            doc.extracted_text = extracted_text
            doc.status = "indexed"
            db.commit()
            logger.info(f"🎉 Background ingestion completed for {doc_id} ({page_count} pages, {chunk_count} chunks).")
    except Exception as exc:
        logger.error(f"❌ Background ingestion failed for document {doc_id}: {exc}", exc_info=True)
        try:
            doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            if doc:
                doc.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        if owns_session:
            db.close()

# Unit tests for Central Control Plane RAGService

import io
import pytest
from rag import rag_service, RAGService
from rag.embedding.config import EmbeddingConfig
from rag.app.factory import RagApplication
from rag.identity.store import InMemoryIdentityStore


@pytest.fixture(autouse=True)
def init_test_rag():
    identity_store = InMemoryIdentityStore()
    cfg = EmbeddingConfig(backend="stub", model_id="stub-v1")
    app = RagApplication.build_in_memory(identity_store, embedding_config=cfg)
    rag_service._app = app
    rag_service._registered_companies.clear()
    rag_service._registered_departments.clear()
    rag_service._registered_users.clear()
    return rag_service


def test_rag_service_ingest_and_retrieve():
    # Ingest document
    doc = rag_service.ingest_document(
        content="راهنمای تنظیمات شبکه و پورت سرور ۸۰۸۰ در سازمان.",
        organization_id="org_alpha",
        team_id="team_devops",
        title="راهنمای شبکه",
        source="network_guide.txt",
    )
    assert doc["document_id"]
    assert doc["status"] == "indexed"
    assert doc["chunk_count"] >= 1

    # Retrieve matching query
    results = rag_service.retrieve(
        query="پورت سرور ۸۰۸۰",
        organization_id="org_alpha",
        team_id="team_devops",
        top_k=2,
    )
    assert len(results) >= 1
    assert "۸۰۸۰" in results[0]["content"]
    assert results[0]["title"] == "راهنمای شبکه"


def test_rag_service_multi_tenant_isolation():
    # Ingest document into org_alpha
    rag_service.ingest_document(
        content="سند محرمانه شرکت آلفا با اطلاعات سری.",
        organization_id="org_alpha",
        team_id="team_it",
        title="سند محرمانه آلفا",
    )

    # Ingest document into org_beta
    rag_service.ingest_document(
        content="اطلاعات عمومی شرکت بتا برای کارمندان.",
        organization_id="org_beta",
        team_id="team_it",
        title="سند بتا",
    )

    # Query from org_beta should NOT see org_alpha content
    beta_results = rag_service.retrieve(
        query="سند محرمانه اطلاعات سری",
        organization_id="org_beta",
        team_id="team_it",
        top_k=5,
    )
    for chunk in beta_results:
        assert "آلفا" not in chunk["content"]
        assert "محرمانه" not in chunk["content"]


def test_rag_service_query_orchestrator():
    rag_service.ingest_document(
        content="سیاست دورکاری شرکت به میزان ۲ روز در هفته برای تمامی تیم‌ها فعال است.",
        organization_id="org_alpha",
        team_id="global",
        title="آیین‌نامه دورکاری",
    )

    q_res = rag_service.query(
        query="شرایط دورکاری چند روز است؟",
        organization_id="org_alpha",
        top_k=3,
    )
    assert len(q_res["citations"]) >= 1
    assert "دورکاری" in q_res["context"]
    assert q_res["citations"][0]["title"] == "آیین‌نامه دورکاری"
    assert q_res["citations"][0]["supportStatus"] == "supported"


def test_rag_service_ingest_file_txt():
    txt_data = "قوانین ساعات کاری از ساعت ۸ صبح الی ۱۶ بعد از ظهر می‌باشد.".encode("utf-8")
    resp = rag_service.ingest_file(
        data=txt_data,
        filename="work_hours.txt",
        organization_id="org_alpha",
        team_id="global",
        title="ساعات کاری",
    )
    assert resp["document_id"]
    assert resp["status"] == "indexed"

    results = rag_service.retrieve(
        query="ساعت کاری شرکت",
        organization_id="org_alpha",
        top_k=1,
    )
    assert len(results) >= 1
    assert "۱۶ بعد از ظهر" in results[0]["content"]


def test_rag_service_delete_document():
    doc = rag_service.ingest_document(
        content="سند موقت برای تست حذف.",
        organization_id="org_alpha",
        team_id="team_temp",
        title="سند موقت",
    )
    doc_id = doc["document_id"]

    results_before = rag_service.retrieve(
        query="سند موقت",
        organization_id="org_alpha",
        team_id="team_temp",
    )
    assert len(results_before) >= 1

    del_ok = rag_service.delete_document(
        document_id=doc_id,
        organization_id="org_alpha",
        team_id="team_temp",
    )
    assert del_ok is True

    results_after = rag_service.retrieve(
        query="سند موقت",
        organization_id="org_alpha",
        team_id="team_temp",
    )
    assert len(results_after) == 0


def test_internal_rag_retrieve_api_endpoint():
    from fastapi.testclient import TestClient
    from server import app

    client = TestClient(app)

    # Ingest a document
    rag_service.ingest_document(
        content="راهنمای جامع امنیت سرورهای ابری در سازمان.",
        organization_id="org_sec",
        team_id="team_infra",
        title="امنیت ابری",
    )

    resp = client.post(
        "/api/rag/retrieve",
        json={
            "query": "امنیت سرورهای ابری",
            "organization_id": "org_sec",
            "team_id": "team_infra",
            "top_k": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert "سرورهای ابری" in data["results"][0]["content"]


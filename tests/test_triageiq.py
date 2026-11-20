"""TriageIQ verification suite - runs fully offline (no API keys)."""
import os
import sys
from pathlib import Path

os.environ["DEMO_MODE"] = "offline"  # force the offline layer before imports
# Hermetic tests: blank any real keys inherited from the shell or a parent
# folder's .env (load_dotenv walks up directories), so results never depend
# on the machine the suite runs on. Empty env values win over .env values
# because load_dotenv does not override existing variables.
os.environ["OPENAI_API_KEY"] = ""
os.environ["PINECONE_API_KEY"] = ""
os.environ["TAVILY_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_settings
from src.ingestion import ingest_directory, ingest_file, _stable_chunk_id, load_file
from src.offline import get_local_kb
from src.self_rag import run_self_rag

ROOT = Path(__file__).resolve().parents[1]


def test_config_matches_reference_defaults():
    s = get_settings()
    assert s.openai_model == "gpt-5-mini"
    assert s.embedding_model == "text-embedding-3-large"
    assert s.embedding_dimension == 3072
    assert s.top_k == 5
    assert s.max_support_retries == 2
    assert s.max_retrieval_rewrites == 2
    assert s.max_web_rewrites == 2
    assert s.pinecone_namespace == "aiops-runbooks"
    assert s.offline_mode is True


def test_ingestion_stable_ids_idempotent():
    kb = get_local_kb()
    first = ingest_directory(ROOT / "documents")
    count_after_first = kb.count()
    second = ingest_directory(ROOT / "documents")
    assert first > 0 and second == first
    assert kb.count() == count_after_first  # stable IDs -> no duplicates
    docs = load_file(ROOT / "documents" / "deployment-rollback-sop.md")
    from langchain_core.documents import Document
    chunk = Document(page_content="hello world")
    assert _stable_chunk_id(ROOT / "documents" / "deployment-rollback-sop.md", chunk, 0) == \
        _stable_chunk_id(ROOT / "documents" / "deployment-rollback-sop.md", chunk, 0)


def test_self_rag_runbook_route_and_memory():
    r1 = run_self_rag("Our online banking API is returning 502 errors after deployment. What should the on-call engineer check first?", "pytest-thread-1")
    assert r1["route"] == "Private Runbooks"
    assert r1["support_status"] == "fully_supported"
    assert r1["usefulness"] == "useful"
    assert any("online-banking-api-runbook" in (s["title"] + s["source"]) for s in r1["sources"])
    assert r1["memory_turns"] == 1
    r2 = run_self_rag("What should I check next if that does not work?", "pytest-thread-1")
    assert r2["memory_turns"] == 2
    assert any("contextualized" in t for t in r2["trace"])


def test_self_rag_no_evidence_route():
    # Operations question with no runbook coverage: retrieval is attempted,
    # evidence stays weak, web fallback has no key -> No Reliable Evidence.
    r = run_self_rag("How do we tune the Kafka consumer lag alert threshold for the telemetry pipeline?", "pytest-thread-2")
    assert r["route"] == "No Reliable Evidence"
    assert r["used_web_search"] is False


def test_self_rag_direct_route_for_generic_question():
    # Reference behaviour: generic questions skip retrieval entirely.
    r = run_self_rag("What is the best sourdough starter feeding schedule for a home bakery?", "pytest-thread-3")
    assert r["route"] == "General Knowledge"


def test_api_endpoints(tmp_path):
    from fastapi.testclient import TestClient
    from app import app
    with TestClient(app) as client:
        h = client.get("/api/health")
        assert h.status_code == 200 and h.json()["service"] == "triageiq-self-rag"
        page = client.get("/")
        assert page.status_code == 200 and "TriageIQ" in page.text
        chat = client.post("/api/chat", json={"question": "CPU on the payments service is above 90%. What is our recommended response procedure?", "thread_id": "pytest-api"})
        assert chat.status_code == 200
        body = chat.json()
        assert body["route"] == "Private Runbooks"
        assert any("payments-high-cpu-runbook" in (s["title"] + s["source"]) for s in body["sources"])
        doc = tmp_path / "atm-offline-runbook.md"
        doc.write_text("# ATM Offline Runbook\n\nWhen an ATM goes offline, check the network circuit status, restart the ATM controller service, verify the switch heartbeat, and escalate to the network team if the circuit is down. Monitor the ATM fleet dashboard for 15 minutes after recovery.", encoding="utf-8")
        up = client.post("/api/upload", files={"file": ("atm-offline-runbook.md", doc.read_bytes(), "text/markdown")})
        assert up.status_code == 200 and up.json()["chunks_indexed"] >= 1
        audits = client.get("/api/audits")
        assert audits.status_code == 200 and len(audits.json()) >= 1

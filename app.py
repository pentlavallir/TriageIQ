from pathlib import Path
import shutil
import time
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from src.config import get_settings
from src.models import ChatRequest, ChatResponse, UploadResponse
from src.self_rag import run_self_rag
from src.ingestion import ingest_file, ingest_directory, namespace, SUPPORTED
from src.db import init_db, save_audit, latest_audits
from src.guardrails import screen_input, redact_pii
from src import integrations, incident_service
from src.metrics import get_metrics
from dotenv import load_dotenv


class AlertRequest(BaseModel):
    source: str = "monitoring"
    alert_name: str = ""
    description: str
    severity_hint: str = ""


class ApproveRequest(BaseModel):
    approver: str


class DeploymentRequest(BaseModel):
    service: str
    version: str
    environment: str = "production"
    status: str = "deployed"

load_dotenv()  # Load environment variables from .env file

ROOT = Path(__file__).resolve().parent
UPLOADS = ROOT / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(
    title="TriageIQ - Enterprise AIOps Incident Response Self-RAG",
    version="2.0.0",
    description="Self-RAG assistant for enterprise IT operations, incident triage, root-cause analysis, and resolution runbooks.",
)

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT / "templates"))


@app.on_event("startup")
def startup():
    init_db()
    # ADAPTATION: in offline mode, pre-load ./documents into the local
    # knowledge base so the demo works out of the box. With real keys the
    # reference flow applies: run `python data_ingestion.py` once first.
    if get_settings().offline_mode:
        from src.offline import get_local_kb
        if get_local_kb().count() == 0:
            ingest_directory(ROOT / "documents")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/health")
def health():
    s = get_settings()
    return {"status": "ok", "service": "triageiq-self-rag", "mode": "offline" if s.offline_mode else "online"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    # Guardrails: screen for prompt injection before anything runs.
    allowed, reason = screen_input(payload.question)
    if not allowed:
        raise HTTPException(status_code=400, detail=reason)
    try:
        started = time.perf_counter()
        result = await run_in_threadpool(run_self_rag, payload.question.strip(), payload.thread_id.strip())
        latency_ms = int((time.perf_counter() - started) * 1000)
        # Privacy: the audit store keeps a PII-redacted copy of the question.
        await run_in_threadpool(save_audit, redact_pii(payload.question), result)
        await run_in_threadpool(integrations.record_chat_metric, latency_ms, result.get("route", ""))
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload", response_model=UploadResponse)
async def upload(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(status_code=400, detail="Supported: PDF, TXT, MD, DOCX")
    safe_name = Path(file.filename).name
    target = UPLOADS / safe_name
    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        count = await run_in_threadpool(ingest_file, target)
        return UploadResponse(filename=safe_name, chunks_indexed=count, namespace=namespace())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audits")
def audits(limit: int = 20):
    return latest_audits(min(max(limit, 1), 100))


# ------------------------------------------------------------ platform layer
# Monitoring -> triage -> Self-RAG -> plan -> HITL approval -> execution,
# with ITSM tickets and DevOps deployment correlation (see COMPARISON.md).
@app.post("/api/alerts")
async def alerts(payload: AlertRequest):
    try:
        return await run_in_threadpool(
            incident_service.handle_alert, payload.source, payload.alert_name,
            payload.description.strip(), payload.severity_hint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/incidents")
def incidents(limit: int = 25):
    return integrations.list_incidents(min(max(limit, 1), 100))


@app.get("/api/incidents/{ticket}")
def incident(ticket: str):
    found = integrations.get_incident(ticket)
    if found is None:
        raise HTTPException(status_code=404, detail=f"Unknown incident ticket: {ticket}")
    return found


@app.post("/api/incidents/{ticket}/approve")
async def approve(ticket: str, payload: ApproveRequest):
    try:
        return await run_in_threadpool(incident_service.approve_incident, ticket, payload.approver)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/deployments")
def create_deployment(payload: DeploymentRequest):
    return integrations.record_deployment(payload.service, payload.version, payload.environment, payload.status)


@app.get("/api/deployments")
def deployments(service: str = "", hours: int = 24):
    return integrations.recent_deployments(service, hours)


@app.get("/api/metrics")
def metrics():
    return get_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)

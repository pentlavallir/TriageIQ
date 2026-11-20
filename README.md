# TriageIQ — Enterprise AIOps Incident Response Self-RAG

A production-style **Self-RAG** platform for enterprise IT operations and incident
response, implementing the user's resume Project 3 (Enterprise AIOps: incident
triage, root-cause analysis, operational knowledge retrieval, resolution
recommendations). It searches private operational knowledge first, self-grades
the retrieved evidence, corrects weak retrieval/generation, and uses **internet
search only when the private knowledge base is insufficient**.

It also demonstrates **LangGraph SQLite persistence memory** so follow-up
questions reuse the same incident context through a stable `thread_id`.

> Engineering provenance: the workflow, project layout and prompts replicate the
> reference implementation the user selected (DSwithBappy's incident-response
> Self-RAG project on GitHub). Every deliberate difference is listed in
> **COMPARISON.md**. The project name, branding and knowledge documents are
> original to TriageIQ.

## Architecture

```
User Incident / Follow-up
        ↓
LangGraph SQLite Memory
        ↓
Contextualize Follow-up
        ↓
Decide Retrieval
        ↓
Private Pinecone Knowledge Base
        ↓
Grade Retrieved Documents
   ┌────┴───────────────┐
Relevant             Weak / Missing
   ↓                      ↓
Generate              Rewrite Query
   ↓                      ↓
IsSUP                 Retry Private KB
   ↓                      ↓
Revise if needed    Internet Search Fallback
   ↓                      ↓
IsUSE                 Grade Web Evidence
   ↓                      ↓
Final Answer ← Generate → IsSUP → IsUSE
        ↓
SQLite Checkpoint / Memory
```

## Tech stack

- **LangGraph** — Self-RAG workflow, conditional routing, persistent thread state
- **OpenAI `gpt-5-mini`** — routing, query rewriting, generation, relevance grading, IsSUP and IsUSE
- **OpenAI `text-embedding-3-large`** — embeddings for private operational documents
- **Pinecone** — private runbooks/SOPs/postmortems knowledge base
- **Tavily** — controlled internet-search fallback
- **SQLite** — LangGraph persistence memory + audit database
- **FastAPI** — application/API backend
- **HTML/CSS/JavaScript** — incident-command-center UI with document upload
- **Docker** — deployment packaging

## Project structure

```
TriageIQ/
├── app.py                     # FastAPI application (python app.py)
├── data_ingestion.py          # ONE file to build the knowledge base
├── src/
│   ├── config.py              # pydantic Settings (single source of truth)
│   ├── db.py                  # SQLite audit log (rag_audit)
│   ├── ingestion.py           # loaders, chunking, stable chunk IDs
│   ├── models.py              # ChatRequest / ChatResponse / UploadResponse
│   ├── self_rag.py            # the 14-node LangGraph Self-RAG workflow
│   ├── vectorstore.py         # Pinecone store, index guard, retriever
│   ├── offline.py             # ADAPTATION: local KB + LLM for key-less demos
│   ├── triage.py              # platform: incident classification agent
│   ├── planner.py             # platform: remediation plan builder
│   ├── executor.py            # platform: HITL-gated runbook execution (simulated)
│   ├── incident_service.py    # platform: alert -> triage -> RAG -> plan -> approve -> execute
│   ├── integrations.py        # platform: monitoring intake, ITSM tickets, deployments
│   ├── metrics.py             # platform: evaluation/operations metrics
│   └── guardrails.py          # platform: injection screening + PII redaction
├── documents/                 # private knowledge base: 13 runbooks/SOPs/postmortems (35 chunks)
│   ├── online-banking-api-runbook.md
│   ├── payments-high-cpu-runbook.md
│   ├── deployment-rollback-sop.md
│   ├── incident-severity-escalation-sop.md
│   ├── database-connection-pool-runbook.md
│   ├── mobile-login-mfa-runbook.md
│   ├── card-authorization-decline-runbook.md
│   ├── atm-network-connectivity-runbook.md
│   ├── api-gateway-5xx-runbook.md
│   ├── kubernetes-crashloop-runbook.md
│   ├── redis-session-cache-runbook.md
│   ├── sample-postmortem-checkout-outage.md
│   └── change-management-sop.md
├── templates/index.html
├── static/styles.css          # Gen Z theme: violet/fuchsia/cyan on deep purple-black
├── static/app.js
├── uploads/                   # documents uploaded through the UI
├── data/                      # SQLite persistence files
├── tests/                     # test_triageiq.py (core) + test_platform.py (platform layer)
├── build.ps1 / build.sh       # one-command end-to-end build
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── LICENSE
└── .env.example
```

## Build end to end (one command)

From the extracted folder:

- Windows (PowerShell): `./build.ps1`
- macOS/Linux: `./build.sh`

The build creates an isolated `.venv`, installs `requirements.txt`, runs the
configuration smoke test (`test.py`), builds the knowledge base
(`data_ingestion.py`), and runs the pytest suite. It is safe to re-run, and it
never touches any other project's environment. When it prints **BUILD OK**,
run the app as below.

## How to run (VS Code + Python only)

Prerequisite: VS Code with the Microsoft **Python** extension.

1. Unzip into a NEW folder, e.g. `C:\TriageIQ`, and open THAT folder in VS Code
   (File > Open Folder).
2. Terminal > New Terminal:
   `python -m venv .venv` then `.venv\Scripts\Activate.ps1` then
   `pip install -r requirements.txt`
   The included `.vscode/settings.json` points VS Code at this `.venv`.
3. **Run without any API keys (offline demo):** just press F5 with
   **"TriageIQ - App (F5)"**, or run `python app.py` in the terminal.
   Offline mode is automatic when no keys are configured: the same LangGraph
   workflow runs against a local knowledge base (data/local_kb.json) and a
   deterministic local model, and `./documents` is loaded on startup.
4. **Run the real stack:** copy `.env.example` to `.env`, fill in
   `OPENAI_API_KEY`, `PINECONE_API_KEY`, `TAVILY_API_KEY`, then build the
   Pinecone knowledge base with ONE command: `python data_ingestion.py`
   (or the F5 config "TriageIQ - Build knowledge base"), then `python app.py`.
5. Open **http://127.0.0.1:8080** — success is the TriageIQ Incident Response
   Console. `/api/health` returns `{"status": "ok", "service": "triageiq-self-rag", "mode": ...}`.
6. **Debug:** set breakpoints in `src/self_rag.py` (e.g. in `grade_relevance`
   or `check_support`), Run and Debug (Ctrl+Shift+D) > "TriageIQ - App (F5)" > F5.
7. **Tests:** `python -m pytest -q` (or the "TriageIQ - Pytest" F5 config).

## Add new documents from the UI

The left-side **Runbook Vault** accepts PDF, TXT, Markdown and DOCX. On
**Add to knowledge base**, the backend uses the exact same ingestion layer and
embedding model as `data_ingestion.py`, into the existing index and namespace.

## LangGraph SQLite persistence memory

Every browser incident session has a persistent `thread_id`. The workflow is
compiled with a SQLite checkpointer storing checkpoints in
`data/langgraph_memory.sqlite`. Example: ask "Our online banking API is
returning 502 errors after deployment. What should I check first?", then ask
"What should I check next if that doesn't work?" — the `contextualize` node
rewrites the follow-up into a standalone question using the persisted context.
In production this layer can be replaced with PostgreSQL or another
production-grade LangGraph checkpointer.

## Recommended demo flow

- **Demo A — Existing knowledge:** "Our online banking API is returning 502
  errors after deployment. What should the on-call engineer check first?"
  Expected route: **Private Runbooks**.
- **Demo B — Persistent memory:** immediately ask "What should I check next if
  that does not work?" — the same `thread_id` reuses the incident context.
- **Demo C — Upload new knowledge:** upload a new runbook from the UI, then ask
  a question whose answer exists only in that document.
- **Demo D — Internet-search fallback:** ask about an issue no runbook covers;
  Self-RAG grades internal evidence, rewrites, then transitions to Internet
  Search (requires `TAVILY_API_KEY`; without it the graph ends cleanly at
  "No Reliable Evidence" instead of crashing).

## Platform layer — resume coverage map

On top of the Self-RAG core, TriageIQ implements the platform capabilities
from the Enterprise AIOps project description (Project 3):

| Resume capability | Where it lives |
|---|---|
| Incident triage, RCA, knowledge retrieval, resolution recommendations | Self-RAG graph (`src/self_rag.py`) + triage agent (`src/triage.py`) |
| Multi-agent workflow: reasoning (triage classification) | `src/triage.py` — severity/category/service/team with auditable signals |
| Planning (remediation steps) | `src/planner.py` — grounded plan extracted from the answer + verification step |
| Execution (runbook actions) | `src/executor.py` — runs only after approval; simulated dry-run mode, clearly labelled |
| Human-in-the-loop, guardrails, fallback to human on-call | Approval gate on every incident; no-evidence incidents auto-escalate (`escalated_to_oncall`) and cannot auto-execute |
| SOPs and escalation policies in agents | Severity/escalation SOP encoded in triage + planner (SEV1 adds a parallel escalation step) |
| Monitoring integration | `POST /api/alerts` webhook intake (Prometheus/Datadog-shaped payload) |
| ITSM integration | Incident tickets `INC-####` in `src/integrations.py` (local store behind the ServiceNow/Jira-shaped interface) |
| DevOps integration | `POST /api/deployments`; recent deployments are correlated onto incidents for RCA |
| Evaluation metrics (quality, retrieval, latency) | `GET /api/metrics` — support rate (IsSUP), usefulness rate (IsUSE), route mix, avg latency, incident counts |
| Security / privacy guardrails | `src/guardrails.py` — prompt-injection screening on chat + alerts; PII redaction before audit storage |

Pipeline: `POST /api/alerts` → triage → Self-RAG → plan → `awaiting_approval`
→ `POST /api/incidents/{ticket}/approve` → simulated execution →
`resolved_simulated`. Try it from the command line after starting the app:

```
curl.exe -X POST http://127.0.0.1:8080/api/alerts -H "Content-Type: application/json" -d '{"source":"prometheus","alert_name":"High5xxRate","description":"Our online banking API is returning 502 errors after deployment. What should the on-call engineer check first?"}'
curl.exe http://127.0.0.1:8080/api/metrics
```

Skipped for now (available on request): Jenkinsfile + Kubernetes manifests,
a standalone evaluation harness over a golden question set, and dashboard
widgets in the web UI (the metrics API above already serves the data).

## Important configuration rule

The application and the ingestion script both import `src/vectorstore.py`, so
they always use the same OpenAI embedding model, embedding dimension, Pinecone
index and namespace. This prevents the common RAG mistake where offline
ingestion and runtime retrieval use different embeddings or namespaces.

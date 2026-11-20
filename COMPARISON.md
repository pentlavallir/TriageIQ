# Comparison — previous build vs the reference GitHub source vs TriageIQ

Reference: `entbappy/CloudOps-Sentinel-Copilot` (GitHub, main @ 3e77dd8), read
file-by-file on 2026-11-19. The previous delivery ("AIOps Sentinel") was built
from the video description before this repo link was available — that is why it
diverged. This file is the honest diff.

## Where the previous build was wrong vs the reference

| Area | Reference repo | Previous build (wrong) |
|---|---|---|
| Layout | `app.py` + `data_ingestion.py` + `src/` package | `app/` package + `run.py` + `scripts/` |
| config | `src/config.py`: pydantic `Settings`, `get_settings()` lru_cache, defaults gpt-5-mini / text-embedding-3-large / dim 3072 / namespace `incident-runbooks` / top_k 5 / three separate retry counters (support, retrieval rewrites, web rewrites) | dataclass with invented fields, gpt-4o-mini, text-embedding-3-small, no dimension, no namespace, one shared retry counter |
| Workflow | 14 LangGraph nodes: contextualize → decide_retrieval → retrieve → grade → rewrite_internal / rewrite_web → web_search → generate → support (IsSUP) → revise → usefulness (IsUSE) → no_answer → commit_memory, all decisions via structured LLM output | 7 hand-rolled nodes; no contextualize, no decide-retrieval, no direct route, no revise loop, no separate web grading loop |
| Memory | LangGraph `SqliteSaver` checkpointer, `data/langgraph_memory.sqlite`, memory as an Annotated list with `operator.add` | hand-rolled SQLite tables in a custom memory module |
| Vector store | Pinecone only, via langchain-pinecone + OpenAIEmbeddings(dimensions=3072), `ensure_index()` dimension guard, retriever k = top_k | custom adapters; local store invented as the primary path |
| Ingestion | langchain loaders (PyPDF/Text) + docx paragraphs, RecursiveCharacterTextSplitter 800/160, stable sha256 chunk IDs | custom chunker 900/150; IDs were random UUIDs at first (duplication bug), later md5 — still not the repo scheme |
| API models | `ChatResponse{answer, route, used_web_search, support_status, usefulness, sources[{type,title,source,url,page}], trace, thread_id, memory_turns}`, `UploadResponse{filename, chunks_indexed, namespace}`, plus `/api/audits` | different response fields (`evidence_grade`, `supported`, `citations`); no audits endpoint |
| UI | incident-command-center console: rail + Runbook Vault upload, metrics strip, session thread_id in localStorage, route/IsSUP/IsUSE/memory tags, workflow-trace viewer | generic three-column chat page |
| Documents | 3 cloud runbooks (checkout API 502, payments high-CPU, rollback SOP) | 10 invented banking runbooks |
| Requirements | langchain stack, jinja2, python-dotenv, langgraph-checkpoint-sqlite, pinecone>=5 | missing langchain/jinja2/dotenv/checkpoint packages |

## Bugs/gaps found in the reference repo itself (fixed in TriageIQ, behaviour otherwise identical)

1. `docker-compose.yml` and `.env.example` are referenced by the README's
   project structure and setup, but are **missing from the repo**. Supplied here.
2. `test.py` prints the raw `OPENAI_API_KEY` to the console. TriageIQ prints
   only whether a key is configured.
3. `web_search` crashes the whole graph when `TAVILY_API_KEY` is not set.
   TriageIQ returns no documents with a trace note, so the graph finishes
   through the normal grade → rewrite → no_answer path.
4. README says open port 8000, but `app.py` serves 8080. TriageIQ documents
   8080 consistently (the Docker CMD also uses 8080).

## Deliberate adaptations in TriageIQ (everything else replicates the reference)

1. **Name/branding:** TriageIQ (unique name; no words from the reference
   project name). Pinecone defaults: index `triageiq-openai-self-rag`,
   namespace `aiops-runbooks`. Persona/domain wording in prompts targets
   enterprise AIOps (the user's resume Project 3); prompt logic is unchanged.
2. **Documents:** the reference's 3 runbooks adapted to a digital-banking
   enterprise (checkout API → online banking API), plus 2 added runbooks
   (severity/escalation SOP, database connection-pool) for the AIOps scope.
   Documents 4–5 are labelled synthetic samples.
3. **Offline demo mode (`src/offline.py`, `DEMO_MODE`):** the reference cannot
   run at all without OpenAI + Pinecone keys. In offline mode the identical
   graph runs against a local knowledge base and a deterministic local model
   implementing the same interfaces, and it makes **no external calls at
   all** — including Tavily, even if a stray key is found in a parent
   folder's `.env` (load_dotenv walks up directories; this made one test
   machine-dependent until fixed on 2026-11-20). With real keys in `.env`,
   none of the offline code executes and behaviour is the reference's. This
   is what makes the build testable end-to-end (6 pytest tests incl. live API
   checks) with no keys.
4. **VS Code support:** `.vscode/launch.json` (4 F5 configs) added — the
   reference ships only a settings file. The user runs VS Code + Python only.
5. **Tests:** `tests/test_triageiq.py` added (the reference has no pytest suite).
6. **Platform layer (added 2026-11-20, beyond the reference):** the reference
   is a Self-RAG chatbot only. To cover the user's full Enterprise AIOps
   resume description, TriageIQ adds `src/triage.py` (classification agent),
   `src/planner.py` (remediation plans), `src/executor.py` (HITL-gated,
   simulated runbook execution), `src/incident_service.py` (alert → triage →
   Self-RAG → plan → approval → execution, with on-call escalation fallback),
   `src/integrations.py` (monitoring intake, ITSM ticket store, DevOps
   deployment correlation, chat latency), `src/metrics.py` +
   `GET /api/metrics`, and `src/guardrails.py` (injection screening, PII
   redaction), exposed via `/api/alerts`, `/api/incidents`,
   `/api/incidents/{ticket}/approve`, `/api/deployments`. The Self-RAG core
   itself is unchanged. Platform tests: `tests/test_platform.py` (3 tests).
   Skipped for now per the user: Jenkins/Kubernetes artifacts, a standalone
   evaluation harness, and UI dashboard widgets.

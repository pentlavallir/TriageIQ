"""Offline demo layer - ADAPTATION, not part of the reference repo.

The reference project raises RuntimeError when OPENAI_API_KEY or
PINECONE_API_KEY is missing, so it cannot run or be tested without paid
accounts. This module implements the SAME interfaces the workflow uses
(a vector store with add_documents/as_retriever, and an LLM with
invoke/with_structured_output) with deterministic local components:

- LocalKnowledgeBase: hashing embeddings + JSON persistence (data/local_kb.json)
- OfflineLLM: heuristic structured decisions + extractive grounded generation

It activates only in offline mode (see Settings.offline_mode). With real
keys configured, none of this code runs and behaviour is the reference's.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from src.config import ROOT

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP = set("the a an and or of to in for on with is are was were be been it its this that at by from as do does did should would can could we our you your i me my what when how why".split())
ACTION_WORDS = ("check", "step", "restart", "rollback", "escalat", "verify", "monitor", "scale", "inspect", "review", "confirm", "compare", "capture", "announce", "restore", "investigate", "disable", "enable", "fail over", "failover")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall((text or "").lower())


def content_words(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in STOP and len(t) > 2}


def _embed(text: str, dim: int = 384) -> list[float]:
    vec = [0.0] * dim
    for tok in tokenize(text):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
        vec[(h >> 8) % dim] += 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


# --------------------------------------------------------------- local KB
class LocalKnowledgeBase:
    """Drop-in for the Pinecone vector store in offline mode."""

    def __init__(self, path: Path | None = None):
        self.path = path or (ROOT / "data" / "local_kb.json")
        self.records: list[dict] = []
        if self.path.exists():
            try:
                self.records = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self.records = []

    def count(self) -> int:
        return len(self.records)

    def add_documents(self, documents: List[Document], ids: List[str] | None = None) -> int:
        ids = ids or [hashlib.md5(d.page_content.encode()).hexdigest() for d in documents]
        by_id = {r["id"]: r for r in self.records}
        for doc, doc_id in zip(documents, ids):
            by_id[doc_id] = {"id": doc_id, "text": doc.page_content,
                              "metadata": doc.metadata or {},
                              "vector": _embed(doc.page_content)}
        self.records = list(by_id.values())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.records), encoding="utf-8")
        return len(documents)

    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        if not self.records:
            return []
        q = _embed(query)
        scored = sorted(self.records, key=lambda r: _cosine(q, r["vector"]), reverse=True)
        return [Document(page_content=r["text"], metadata=dict(r["metadata"])) for r in scored[:k]]

    def as_retriever(self, search_kwargs: dict | None = None):
        return _LocalRetriever(self, k=(search_kwargs or {}).get("k", 5))


class _LocalRetriever:
    def __init__(self, store: LocalKnowledgeBase, k: int = 5):
        self.store, self.k = store, k

    def invoke(self, query: str) -> List[Document]:
        return self.store.similarity_search(query, k=self.k)


_local_kb: LocalKnowledgeBase | None = None


def get_local_kb() -> LocalKnowledgeBase:
    global _local_kb
    if _local_kb is None:
        _local_kb = LocalKnowledgeBase()
    return _local_kb


# --------------------------------------------------------------- offline LLM
EXPANSIONS = {
    "login": "login authentication MFA sign-on access failure",
    "mfa": "MFA multi factor authentication passcode login",
    "502": "502 bad gateway upstream deployment rollback readiness probe",
    "503": "503 service unavailable gateway upstream",
    "cpu": "CPU saturation high utilization latency scaling replica",
    "payment": "payments authorization CPU latency",
    "card": "card authorization decline payments",
    "database": "database connection pool exhaustion",
    "pool": "connection pool exhaustion database",
    "rollback": "rollback deployment last known healthy version verify",
    "deploy": "deployment release rollback version",
    "atm": "ATM network connectivity offline",
    "gateway": "API gateway 5xx upstream latency",
}
OPS_HINTS = ("error", "outage", "down", "fail", "incident", "cpu", "latency", "502", "503", "500",
             "login", "mfa", "deploy", "rollback", "database", "pool", "gateway", "payment", "card",
             "atm", "crashloop", "pod", "kubernetes", "memory", "disk", "timeout", "runbook", "escalat",
             "severity", "sev1", "sev2", "check", "service", "api", "users cannot", "members cannot",
             "kafka", "alert", "lag", "telemetry", "threshold", "queue", "consumer", "monitoring")


def _msg_text(messages) -> str:
    parts = []
    for m in messages or []:
        parts.append(getattr(m, "content", str(m)))
    return "\n".join(parts)


def _section(text: str, start: str, ends: tuple[str, ...]) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    i += len(start)
    j = len(text)
    for e in ends:
        k = text.find(e, i)
        if 0 <= k < j:
            j = k
    return text[i:j].strip()


class _Structured:
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, messages):
        text = _msg_text(messages)
        name = self.schema.__name__
        if name == "RetrieveDecision":
            q = _section(text, "Question:", ()).lower()
            return self.schema(should_retrieve=any(h in q for h in OPS_HINTS))
        if name == "RelevanceDecision":
            q = _section(text, "Question:", ("\nDocument:",))
            doc = _section(text, "Document:", ())
            overlap = len(content_words(q) & content_words(doc))
            return self.schema(is_relevant=overlap >= 3)
        if name == "QueryRewrite":
            newest = _section(text, "Newest message:", ())
            if newest:  # contextualize call
                history = _section(text, "Previous conversation:", ("\nNewest message:",))
                prev_users = [ln[6:].strip() for ln in history.splitlines() if ln.startswith("User: ")]
                follow = any(w in newest.lower() for w in ("next", "that", "it ", "then", "else", "what about", "still", "after that"))
                if prev_users and follow:
                    return self.schema(query=f"{prev_users[-1]} Follow-up: {newest}")
                return self.schema(query=newest)
            q = _section(text, "Question:", ("\nPrevious",))
            extra = [exp for key, exp in EXPANSIONS.items() if key in q.lower()]
            return self.schema(query=(q + " " + " ".join(extra)).strip())
        if name == "SupportDecision":
            ans = _section(text, "Answer:", ("\nEvidence:",))
            ev = _section(text, "Evidence:", ())
            aw, ew = content_words(ans), content_words(ev)
            overlap = (len(aw & ew) / len(aw)) if aw else 0.0
            status = "fully_supported" if overlap >= 0.45 else ("partially_supported" if overlap >= 0.2 else "no_support")
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ev.replace("\n", " ")) if s.strip()]
            return self.schema(status=status, evidence=sents[:2])
        if name == "UsefulnessDecision":
            ans = _section(text, "Answer:", ())
            useful = len(ans) >= 120 and any(w in ans.lower() for w in ACTION_WORDS)
            return self.schema(status="useful" if useful else "not_useful",
                               reason="Answer gives concrete incident actions." if useful else "Answer lacks actionable incident steps.")
        raise ValueError(f"OfflineLLM does not know schema {name}")


class OfflineLLM:
    """Deterministic stand-in for ChatOpenAI in offline mode."""

    def with_structured_output(self, schema):
        return _Structured(schema)

    def invoke(self, messages):
        text = _msg_text(messages)
        if "Evidence:" in text:  # generate_from_context / revise_answer
            ev = _section(text, "Evidence:", ())
            q = _section(text, "Question:", ("\nEvidence:", "\nCurrent answer:"))
            return AIMessage(content=_extractive_answer(q, ev))
        if "general technical knowledge only" in text:  # generate_direct
            q = getattr(messages[-1], "content", "") if messages else text
            return AIMessage(content=f"General guidance (no runbook evidence used): {q.strip()} is a general technical topic. "
                                     "For production incidents, ask with the service name and symptom so the runbooks can be searched.")
        return AIMessage(content="")


def _extractive_answer(question: str, evidence: str) -> str:
    if not evidence.strip():
        return "I do not have enough evidence in the knowledge base to answer this incident question."
    qwords = content_words(question)
    blocks = [b.strip() for b in evidence.split("---") if b.strip()]
    lines: list[str] = []
    for block in blocks:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", block.replace("\n", " ")) if s.strip()]
        ranked = sorted(sents, key=lambda s: len(qwords & content_words(s)), reverse=True)
        for s in ranked:
            if len(qwords & content_words(s)) > 0 and s not in lines:
                lines.append(s)
            if len(lines) >= 7:
                break
        if len(lines) >= 7:
            break
    if not lines:
        lines = [evidence.replace("\n", " ")[:400]]
    return "Based on the runbook evidence: " + " ".join(lines)

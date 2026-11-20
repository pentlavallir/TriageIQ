"""Operational metrics for dashboards and production evaluation.

Platform layer (resume: "defined production evaluation metrics for
recommendation quality, retrieval performance, latency, and monitoring").
Aggregates the Self-RAG audit log (data/audit.db), chat latency records and
the incident store (data/platform.db) into one dashboard-ready payload.
"""
from __future__ import annotations

import sqlite3

from src import integrations
from src.config import get_settings


def get_metrics() -> dict:
    metrics: dict = {"chats": 0, "routes": {}, "support_rate": None,
                     "usefulness_rate": None, "avg_latency_ms": None,
                     "incidents": {"total": 0, "awaiting_approval": 0,
                                   "resolved_simulated": 0, "escalated_to_oncall": 0}}
    audit_path = get_settings().database_file
    try:
        with sqlite3.connect(audit_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT route, support_status, usefulness FROM rag_audit").fetchall()
        metrics["chats"] = len(rows)
        supported = useful = s_total = u_total = 0
        for r in rows:
            metrics["routes"][r["route"] or "unknown"] = metrics["routes"].get(r["route"] or "unknown", 0) + 1
            if r["support_status"]:
                s_total += 1
                supported += 1 if r["support_status"] == "fully_supported" else 0
            if r["usefulness"]:
                u_total += 1
                useful += 1 if r["usefulness"] == "useful" else 0
        metrics["support_rate"] = round(supported / s_total, 3) if s_total else None
        metrics["usefulness_rate"] = round(useful / u_total, 3) if u_total else None
    except sqlite3.Error:
        pass
    try:
        with integrations._conn() as conn:
            row = conn.execute("SELECT AVG(latency_ms) AS avg_ms FROM chat_metrics").fetchone()
            if row and row["avg_ms"] is not None:
                metrics["avg_latency_ms"] = round(row["avg_ms"])
            for r in conn.execute("SELECT status, COUNT(*) AS n FROM incidents GROUP BY status").fetchall():
                metrics["incidents"]["total"] += r["n"]
                if r["status"] in metrics["incidents"]:
                    metrics["incidents"][r["status"]] = r["n"]
    except sqlite3.Error:
        pass
    return metrics

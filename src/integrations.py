"""Enterprise integrations: monitoring intake, ITSM tickets, DevOps events.

Platform layer (resume: "integrated with enterprise monitoring systems,
ITSM platforms, and DevOps tooling"). These adapters keep the exact shapes
a production integration uses - a monitoring webhook payload in, an ITSM
incident record with a ticket id, a deployment event stream for change
correlation - persisted in a local SQLite store (data/platform.db). In a
production deployment each function is backed by the real system
(Prometheus/Datadog webhook, ServiceNow/Jira REST, CI/CD deploy events)
behind the same interface.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.config import ROOT

DB_PATH = ROOT / "data" / "platform.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            ticket TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            source TEXT, alert_name TEXT, description TEXT,
            severity TEXT, category TEXT, service TEXT, owning_team TEXT,
            route TEXT, answer TEXT, plan_json TEXT,
            status TEXT, approver TEXT, execution_json TEXT,
            correlated_deployments_json TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deployments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            service TEXT, version TEXT, environment TEXT, status TEXT
        )""")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            latency_ms INTEGER, route TEXT
        )""")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_ticket(conn) -> str:
    row = conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()
    return f"INC-{row['n'] + 1:04d}"


# --------------------------------------------------------------- ITSM store
def create_incident(source: str, alert_name: str, description: str, triage: dict,
                    route: str, answer: str, plan: list[dict], status: str,
                    correlated: list[dict]) -> dict:
    with _conn() as conn:
        ticket = _next_ticket(conn)
        conn.execute(
            """INSERT INTO incidents (ticket, created_at, source, alert_name, description,
               severity, category, service, owning_team, route, answer, plan_json, status,
               correlated_deployments_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ticket, _now(), source, alert_name, description, triage.get("severity"),
             triage.get("category"), triage.get("service"), triage.get("owning_team"),
             route, answer, json.dumps(plan), status, json.dumps(correlated)),
        )
        conn.commit()
    return get_incident(ticket)


def get_incident(ticket: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE ticket = ?", (ticket,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    d["plan"] = json.loads(d.pop("plan_json") or "[]")
    d["execution"] = json.loads(d.pop("execution_json") or "null")
    d["correlated_deployments"] = json.loads(d.pop("correlated_deployments_json") or "[]")
    return d


def list_incidents(limit: int = 25) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT ticket FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [get_incident(r["ticket"]) for r in rows]


def update_incident(ticket: str, status: str, approver: str = "", execution: list[dict] | None = None) -> dict | None:
    with _conn() as conn:
        conn.execute(
            "UPDATE incidents SET status = ?, approver = ?, execution_json = ? WHERE ticket = ?",
            (status, approver, json.dumps(execution) if execution is not None else None, ticket),
        )
        conn.commit()
    return get_incident(ticket)


# --------------------------------------------------------------- DevOps events
def record_deployment(service: str, version: str, environment: str, status: str) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO deployments (created_at, service, version, environment, status) VALUES (?,?,?,?,?)",
            (_now(), service, version, environment, status),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM deployments WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


def recent_deployments(service: str = "", hours: int = 24, limit: int = 20) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with _conn() as conn:
        if service and service != "unknown":
            rows = conn.execute(
                "SELECT * FROM deployments WHERE created_at >= ? AND service = ? ORDER BY created_at DESC LIMIT ?",
                (since, service, limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM deployments WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                (since, limit)).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------- chat metrics
def record_chat_metric(latency_ms: int, route: str) -> None:
    with _conn() as conn:
        conn.execute("INSERT INTO chat_metrics (created_at, latency_ms, route) VALUES (?,?,?)",
                     (_now(), latency_ms, route))
        conn.commit()

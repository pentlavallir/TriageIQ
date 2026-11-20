"""Incident pipeline orchestration.

Platform layer tying the agents together the way the resume describes:
monitoring alert -> triage classification (reasoning) -> Self-RAG resolution
(retrieval + recommendation) -> remediation plan (planning) -> human
approval (HITL) -> execution -> ITSM ticket update, with automatic
escalation to the human on-call when evidence is insufficient (fallback).

Deployment events for the affected service are correlated onto the
incident for root-cause context (change is the top incident cause).
"""
from __future__ import annotations

from src import integrations
from src.guardrails import redact_pii, screen_input
from src.planner import build_plan
from src.self_rag import run_self_rag
from src.triage import classify_incident
from src.executor import execute_plan


def handle_alert(source: str, alert_name: str, description: str, severity_hint: str = "") -> dict:
    allowed, reason = screen_input(description)
    if not allowed:
        raise ValueError(reason)
    safe_description = redact_pii(description)
    triage = classify_incident(safe_description, severity_hint)
    correlated = integrations.recent_deployments(triage["service"], hours=24)
    result = run_self_rag(safe_description, thread_id=f"alert-{alert_name or 'monitoring'}")
    plan = build_plan(result["answer"], triage, result.get("sources", []))
    if result["route"] == "No Reliable Evidence":
        # Fallback to human on-call: no safe automated recommendation exists.
        status = "escalated_to_oncall"
    else:
        status = "awaiting_approval"
    incident = integrations.create_incident(
        source=source, alert_name=alert_name, description=safe_description,
        triage=triage, route=result["route"], answer=result["answer"],
        plan=plan, status=status, correlated=correlated,
    )
    incident["support_status"] = result.get("support_status", "")
    incident["usefulness"] = result.get("usefulness", "")
    incident["sources"] = result.get("sources", [])
    incident["triage"] = triage
    return incident


def approve_incident(ticket: str, approver: str) -> dict:
    incident = integrations.get_incident(ticket)
    if incident is None:
        raise KeyError(f"Unknown incident ticket: {ticket}")
    if incident["status"] == "escalated_to_oncall":
        raise ValueError("Incident is escalated to the human on-call; automated execution is not available.")
    if incident["status"] not in {"awaiting_approval"}:
        raise ValueError(f"Incident {ticket} is in status '{incident['status']}' and cannot be approved.")
    execution = execute_plan(incident["plan"], approver)
    return integrations.update_incident(ticket, status="resolved_simulated",
                                        approver=approver, execution=execution)

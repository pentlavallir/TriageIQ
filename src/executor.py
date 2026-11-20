"""Runbook action executor with a human-in-the-loop gate.

Platform layer (resume: multi-agent workflow - "execution (runbook
actions)"; "semi-autonomous agents, applying human-in-the-loop, guardrails,
and fallback to human on-call where required").

Safety contract:
- NOTHING executes without an explicit human approval recorded on the
  incident (approve_incident in incident_service). There is no auto-run path.
- In this build the executor runs in SIMULATED mode: each approved step is
  dry-run and reported as simulated_success, clearly labelled, and no
  production system is touched. The step loop is where production runbook
  automation (SSH/REST/Kubernetes actions) plugs in behind the same gate.
"""
from __future__ import annotations

from datetime import datetime, timezone


def execute_plan(plan: list[dict], approver: str) -> list[dict]:
    results = []
    for step in plan:
        results.append({
            "step": step.get("step"),
            "action": step.get("action"),
            "kind": step.get("kind", "runbook_action"),
            "status": "simulated_success",
            "detail": "Dry-run only (simulated execution mode): no production system was modified.",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "approved_by": approver,
        })
    return results

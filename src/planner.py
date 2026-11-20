"""Remediation planner.

Platform layer (resume: multi-agent workflow - "planning (remediation
steps)"). Converts a grounded Self-RAG answer into an ordered, reviewable
remediation plan. Steps are extracted from the answer's own action
sentences, so the plan never invents actions the evidence did not support;
a verification step is always appended, and SEV1 plans carry an explicit
escalation step. The plan is what a human approves in the HITL gate before
the executor runs anything.
"""
from __future__ import annotations

import re

_ACTION_HINTS = ("check", "verify", "inspect", "review", "compare", "restart", "roll back",
                 "rollback", "scale", "capture", "announce", "confirm", "restore",
                 "escalate", "monitor", "disable", "enable", "restart")


def build_plan(answer: str, triage: dict, sources: list[dict]) -> list[dict]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", (answer or "").replace("\n", " ")) if s.strip()]
    steps: list[dict] = []
    seen = set()
    for s in sentences:
        if any(h in s.lower() for h in _ACTION_HINTS) and s not in seen and len(s) > 25:
            seen.add(s)
            steps.append({"step": len(steps) + 1, "action": s, "kind": "runbook_action"})
        if len(steps) >= 6:
            break
    if not steps:
        steps.append({"step": 1, "action": "Follow the resolution recommendation in the incident answer step by step.", "kind": "runbook_action"})
    steps.append({
        "step": len(steps) + 1,
        "action": "Verify recovery: error rate and latency back to baseline and stable for 15 minutes before closing the incident.",
        "kind": "verification",
    })
    if triage.get("severity") == "SEV1":
        steps.append({
            "step": len(steps) + 1,
            "action": f"Escalate in parallel to the incident commander and the {triage.get('owning_team', 'service owner')} (SEV1 policy).",
            "kind": "escalation",
        })
    return steps

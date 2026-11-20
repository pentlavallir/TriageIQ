"""Incident triage classification agent.

Platform layer (resume: multi-agent workflow - "reasoning (triage
classification)"). Deterministic and explainable: the same classifier runs
in offline and online mode, and every classification carries the signals
that produced it, so an SRE can audit why an incident was routed.

Outputs: severity (SEV1-SEV3, aligned to documents/incident-severity-
escalation-sop.md), category, service, owning team, and the matched signals.
"""
from __future__ import annotations

_SEV1_SIGNALS = ("outage", "is down", "service down", "unavailable", "cannot log in",
                 "can't log in", "login failing for all", "all tunnels", "dropped all",
                 "payments failing", "data loss", "security breach")
_SEV2_SIGNALS = ("502", "503", "500 error", "error rate", "high cpu", "latency",
                 "pool exhaustion", "connection pool", "decline spike", "crashloop",
                 "restarting", "timeout", "degraded", "elevated errors", "queue depth")
_CATEGORY_SIGNALS = {
    "deployment": ("deployment", "deploy", "release", "rollback", "version", "after the upgrade", "after upgrade"),
    "database": ("database", "connection pool", "pool exhaustion", "sql", "query", "db "),
    "network": ("vpn", "tunnel", "network", "dns", "circuit", "connectivity"),
    "performance": ("cpu", "latency", "slow", "memory", "disk", "saturation"),
    "security": ("breach", "unauthorized", "certificate", "auth", "mfa", "login"),
    "availability": ("502", "503", "down", "outage", "unavailable", "crashloop", "restarting"),
}
_SERVICE_SIGNALS = {
    "online-banking-api": ("online banking", "banking api"),
    "payments": ("payment", "card authorization", "decline"),
    "vpn-gateway": ("vpn", "tunnel"),
    "accounts-database": ("database", "connection pool"),
}
_TEAM_BY_CATEGORY = {
    "database": "database on-call",
    "network": "network on-call",
    "security": "security on-call",
    "deployment": "platform on-call",
    "performance": "service owner",
    "availability": "service owner",
    "general": "service owner",
}


def classify_incident(text: str, severity_hint: str = "") -> dict:
    lowered = (text or "").lower()
    signals: list[str] = []

    severity = "SEV3"
    if severity_hint.upper() in {"SEV1", "SEV2", "SEV3"}:
        severity = severity_hint.upper()
        signals.append(f"severity hint from source: {severity}")
    elif any(s in lowered for s in _SEV1_SIGNALS):
        severity = "SEV1"
        signals += [f"SEV1 signal: '{s}'" for s in _SEV1_SIGNALS if s in lowered][:2]
    elif any(s in lowered for s in _SEV2_SIGNALS):
        severity = "SEV2"
        signals += [f"SEV2 signal: '{s}'" for s in _SEV2_SIGNALS if s in lowered][:2]
    else:
        signals.append("no SEV1/SEV2 signal matched - default SEV3")

    category = "general"
    best = 0
    for cat, words in _CATEGORY_SIGNALS.items():
        hits = [w for w in words if w in lowered]
        if len(hits) > best:
            category, best = cat, len(hits)
            signals.append(f"category signals: {', '.join(hits[:3])}")

    service = "unknown"
    for svc, words in _SERVICE_SIGNALS.items():
        if any(w in lowered for w in words):
            service = svc
            break

    return {
        "severity": severity,
        "category": category,
        "service": service,
        "owning_team": _TEAM_BY_CATEGORY.get(category, "service owner"),
        "signals": signals,
    }

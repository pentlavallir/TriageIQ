"""Guardrails - security, privacy and data-handling controls.

Platform layer (resume: "alignment with security, privacy, and data-handling
policies; operationalize guardrails"). Applied at the API boundary:

- screen_input: blocks prompt-injection / instruction-extraction attempts.
- redact_pii: masks emails, phone numbers and long digit sequences before
  text is written to audit/incident stores, so operational logs do not
  accumulate personal data.
"""
from __future__ import annotations

import re

_INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) instructions",
    r"disregard (all )?(previous|prior|above)",
    r"reveal (your )?(system prompt|instructions|prompt)",
    r"show me your (system prompt|instructions)",
    r"you are now (a|an|in)",
    r"developer mode",
    r"jailbreak",
    r"print your (instructions|prompt|api key)",
    r"what is your (api key|system prompt)",
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
_LONG_DIGITS_RE = re.compile(r"\b\d{9,}\b")


def screen_input(text: str) -> tuple[bool, str]:
    """Return (allowed, reason). Blocks known prompt-injection shapes."""
    lowered = (text or "").lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return False, "Blocked by guardrails: prompt-injection pattern detected."
    return True, ""


def redact_pii(text: str) -> str:
    """Mask PII before persistence in audit / incident stores."""
    if not text:
        return text
    text = _EMAIL_RE.sub("[email-redacted]", text)
    text = _PHONE_RE.sub("[phone-redacted]", text)
    text = _LONG_DIGITS_RE.sub("[number-redacted]", text)
    return text

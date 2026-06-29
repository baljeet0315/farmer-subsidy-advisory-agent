"""Guardrails and fallback logic.

Enforces responsible-use rules: grounding checks (no scheme claims outside the
retrieved KB), mandatory "verify locally" disclaimer, graceful handling of
empty retrieval / API failure / unknown input, and no legal-financial
guarantees.

TODO (Day 8):
- ground_check(llm_output, passages) -> bool
- apply(checklist) -> checklist (adds disclaimers, strips unsafe claims)
- fallback(reason) -> safe message
"""
from __future__ import annotations


def ground_check(llm_output: str, passages: list[str]) -> bool:
    """Verify claims are supported by retrieved passages. TODO: implement."""
    raise NotImplementedError


def fallback(reason: str) -> str:
    """Return a safe fallback message for an error/edge case. TODO: implement."""
    raise NotImplementedError

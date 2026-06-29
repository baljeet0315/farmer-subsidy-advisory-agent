"""Confidence engine + human-routing logic.

Combines three signals into a per-scheme confidence:
  1. rules verdict (the anchor)
  2. model-model agreement (Claude vs OpenAI)
  3. model-rules agreement
Low confidence -> needs_human_review = True (routed to reviewer queue).
Thresholds come from .env (CONFIDENCE_HIGH / CONFIDENCE_LOW), tuned on eval.

TODO (Day 6):
- score(rules_verdict, claude_out, openai_out) -> EligibilityResult
- map score -> High/Medium/Low and set needs_human_review.
"""
from __future__ import annotations

from .models import EligibilityResult


def score(rules_verdict: bool, claude_out: dict, openai_out: dict) -> EligibilityResult:
    """Compute confidence and routing for one scheme. TODO: implement."""
    raise NotImplementedError

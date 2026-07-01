"""Confidence engine + human-routing logic.

Combines the deterministic rules verdict with a three-model ensemble into a
per-scheme confidence:
  1. rules verdict (the anchor)
  2. inter-model agreement — majority vote across Claude / OpenAI / Gemini
  3. model-rules agreement — do the models agree with the deterministic engine?
An odd number of models gives clean majority tie-breaking. Low confidence
(models split, or majority contradicts rules) -> needs_human_review = True
(routed to the reviewer queue). Thresholds come from .env
(CONFIDENCE_HIGH / CONFIDENCE_LOW), tuned on the eval set.

TODO (Day 6):
- score(rules_verdict, model_outputs: dict) -> EligibilityResult
- map score -> High/Medium/Low and set needs_human_review.
- a model that abstained (API error) is excluded from the vote, not counted against.
"""
from __future__ import annotations

from .models import EligibilityResult


def score(rules_verdict: bool, model_outputs: dict[str, dict]) -> EligibilityResult:
    """Compute confidence and routing for one scheme from the 3-model outputs. TODO: implement."""
    raise NotImplementedError

"""Three-LLM reasoning layer (Claude + OpenAI + Gemini).

Sends the same grounded prompt to all three models in parallel, parses each into
a structured eligibility + explanation, and returns them for the confidence
engine to compare. LLMs explain retrieved content; they do not decide hard
eligibility (the rules engine does).

TODO (Day 5):
- reason_claude / reason_openai / reason_gemini(profile, scheme, passages) -> structured dict
- reason_all(...) -> {"claude": ..., "openai": ..., "gemini": ...}, run concurrently
- Robust JSON parsing + per-model retry/fallback on API error (a model that
  errors is recorded as abstaining, not counted in agreement).
"""
from __future__ import annotations

from .models import FarmerProfile, Scheme

MODELS = ("claude", "openai", "gemini")


def reason_all(
    profile: FarmerProfile, scheme: Scheme, passages: list[str]
) -> dict[str, dict]:
    """Return {model_name: structured_reasoning} for all three models. TODO: implement."""
    raise NotImplementedError

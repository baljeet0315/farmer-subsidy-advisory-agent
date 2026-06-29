"""Two-LLM reasoning layer (Claude + OpenAI).

Sends the same grounded prompt to both models in parallel, parses each into a
structured eligibility + explanation, and returns both for the confidence
engine to compare. LLMs explain retrieved content; they do not decide hard
eligibility (the rules engine does).

TODO (Day 5):
- reason_claude(profile, scheme, passages) -> structured dict
- reason_openai(profile, scheme, passages) -> structured dict
- reason_both(...) -> (claude_out, openai_out), run concurrently
- Robust JSON parsing + retry/fallback on API error.
"""
from __future__ import annotations

from .models import FarmerProfile, Scheme


def reason_both(
    profile: FarmerProfile, scheme: Scheme, passages: list[str]
) -> tuple[dict, dict]:
    """Return (claude_output, openai_output) structured reasoning. TODO: implement."""
    raise NotImplementedError

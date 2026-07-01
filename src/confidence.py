"""Confidence engine + human-routing logic.

The deterministic rules engine is the ANCHOR: the delivered eligibility verdict
is always the rules verdict. The three LLMs vote INDEPENDENTLY; their agreement
with each other and with the rules produces a confidence signal that decides
whether a result is auto-delivered or flagged for human review.

Signals (per scheme):
  - unanimity     : fraction of responding models that agree with the model
                    majority  (1.0 = all models agree)
  - corroboration : fraction of responding models that agree with the rules
                    verdict  (1.0 = every model backs the rules)

  confidence_score = 0.4 * unanimity + 0.6 * corroboration
      (rules-corroboration weighted higher — the rules are the source of truth)

Routing -> needs_human_review = True when ANY of:
  - no model responded (whole ensemble abstained/errored)
  - the model majority CONTRADICTS the rules verdict
  - confidence_score < CONFIDENCE_LOW
A model that errored or returned "unknown" abstains and is excluded from the vote.

Bands: score >= CONFIDENCE_HIGH -> HIGH; >= CONFIDENCE_LOW -> MEDIUM; else LOW.
Thresholds come from .env (CONFIDENCE_HIGH / CONFIDENCE_LOW).
"""
from __future__ import annotations

import os

from .models import Confidence, EligibilityResult

HIGH = float(os.getenv("CONFIDENCE_HIGH", "0.8"))
LOW = float(os.getenv("CONFIDENCE_LOW", "0.5"))


def _band(score: float) -> Confidence:
    if score >= HIGH:
        return Confidence.HIGH
    if score >= LOW:
        return Confidence.MEDIUM
    return Confidence.LOW


def score(scheme_id: str, rules_verdict: bool, model_outputs: dict[str, dict]) -> EligibilityResult:
    """Combine the rules verdict + 3-model votes into an EligibilityResult."""
    # Collect boolean votes from models that actually decided (exclude abstain).
    votes: list[bool] = []
    for out in model_outputs.values():
        if out.get("ok") and isinstance(out.get("eligible"), bool):
            votes.append(out["eligible"])

    n = len(votes)
    if n == 0:
        return EligibilityResult(
            scheme_id=scheme_id, eligible=rules_verdict, rules_verdict=rules_verdict,
            reason="No model produced a usable vote; deferring to human review.",
            confidence=Confidence.LOW, confidence_score=0.0,
            needs_human_review=True, model_agreement=None,
        )

    true_votes = sum(votes)
    majority_value = true_votes >= (n - true_votes)  # ties -> True (eligible)
    majority_count = max(true_votes, n - true_votes)
    unanimity = majority_count / n
    corroboration = sum(1 for v in votes if v == rules_verdict) / n

    confidence_score = round(0.4 * unanimity + 0.6 * corroboration, 2)
    band = _band(confidence_score)
    # A single responding model is not enough to earn HIGH confidence.
    if n < 2 and band == Confidence.HIGH:
        band = Confidence.MEDIUM
    majority_conflicts_rules = majority_value != rules_verdict

    needs_review = majority_conflicts_rules or band == Confidence.LOW

    agree_txt = f"{sum(1 for v in votes if v == rules_verdict)}/{n} models agree with the rules verdict"
    if majority_conflicts_rules:
        reason = f"Model majority disagrees with the deterministic rules ({agree_txt}); flagged for review."
    elif needs_review:
        reason = f"Low agreement ({agree_txt}); flagged for review."
    else:
        reason = f"{agree_txt}; confidence {band.value}."

    return EligibilityResult(
        scheme_id=scheme_id, eligible=rules_verdict, rules_verdict=rules_verdict,
        reason=reason, confidence=band, confidence_score=confidence_score,
        needs_human_review=needs_review, model_agreement=round(unanimity, 2),
    )

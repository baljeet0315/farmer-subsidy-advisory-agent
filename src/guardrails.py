"""Guardrails and fallback logic.

Enforces responsible-use rules on top of the LLM layer:
- ground_check(): a lexical grounding heuristic — how much of a model's claim is
  actually supported by the retrieved passages. Complements each model's own
  self-reported "grounded" flag and drives the grounding-rate metric. (Heuristic
  and English-oriented; meant as a defensive signal, not a proof.)
- DISCLAIMER / apply_disclaimer(): the mandatory "verify locally" note.
- fallback(): safe messages for empty retrieval / API failure / unknown input.
- is_out_of_scope(): true when no retrieved passage is relevant enough.
"""
from __future__ import annotations

import re

DISCLAIMER = ("This is guidance only — please verify with your local agriculture "
             "office / Common Service Centre (CSC) before acting.")

# Chroma cosine distance beyond which a passage is treated as irrelevant.
RELEVANCE_MAX_DISTANCE = 1.35

_STOPWORDS = {
    "the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "at", "is", "are",
    "you", "your", "with", "this", "that", "will", "can", "may", "be", "as", "if",
    "by", "from", "it", "not", "no", "do", "does", "have", "has", "who", "what",
    "which", "any", "all", "per", "into", "up", "out", "so", "than", "then", "them",
}


def _content_words(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 2]


def ground_check(claim: str, passages: list[str], threshold: float = 0.55) -> tuple[bool, float]:
    """Return (grounded, overlap_score) — fraction of the claim's content words
    that appear in the retrieved passages. Empty claim counts as grounded."""
    claim_words = set(_content_words(claim))
    if not claim_words:
        return True, 1.0
    corpus = set(_content_words(" ".join(passages)))
    overlap = len(claim_words & corpus) / len(claim_words)
    return overlap >= threshold, round(overlap, 2)


def apply_disclaimer(text: str) -> str:
    if DISCLAIMER.split(" —")[0].lower() in (text or "").lower():
        return text
    return f"{text}\n\n{DISCLAIMER}" if text else DISCLAIMER


def is_out_of_scope(hits: list[dict], max_distance: float = RELEVANCE_MAX_DISTANCE) -> bool:
    """True when no retrieved passage is close enough to be relevant."""
    return not any(h.get("distance", 99) <= max_distance for h in hits)


def fallback(reason: str) -> str:
    messages = {
        "no_retrieval": "I couldn't find relevant scheme information for that. Please ask "
                        "about the farmer schemes, or verify with your local office.",
        "api_error": "The assistant is temporarily unavailable. Please try again shortly; "
                     "meanwhile you can verify scheme details at your local agriculture office / CSC.",
        "unknown_input": "I didn't quite understand. Could you share your farm details "
                         "(land size, ownership, crop, irrigation) so I can help?",
    }
    return messages.get(reason, messages["no_retrieval"])

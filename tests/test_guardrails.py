"""Offline tests for guardrails + i18n."""
from __future__ import annotations

from src import guardrails, i18n


PASSAGES = [
    "PM-KUSUM gives a subsidy for a stand-alone solar agriculture pump up to 7.5 HP. "
    "Documents required: Aadhaar card, land records, bank account.",
]


def test_ground_check_supported_claim():
    claim = "You can get a subsidy for a solar pump; bring your Aadhaar and land records."
    grounded, score = guardrails.ground_check(claim, PASSAGES)
    assert grounded and score >= 0.55


def test_ground_check_unsupported_claim():
    claim = "You will receive a free tractor and a monthly cash pension of fifty thousand rupees."
    grounded, score = guardrails.ground_check(claim, PASSAGES)
    assert not grounded


def test_ground_check_empty_claim_is_grounded():
    grounded, score = guardrails.ground_check("", PASSAGES)
    assert grounded and score == 1.0


def test_is_out_of_scope():
    assert guardrails.is_out_of_scope([{"distance": 1.9}, {"distance": 1.5}])
    assert not guardrails.is_out_of_scope([{"distance": 0.7}])


def test_apply_disclaimer_adds_once():
    once = guardrails.apply_disclaimer("Here is your answer.")
    assert "verify with your local" in once.lower()
    twice = guardrails.apply_disclaimer(once)
    assert twice.lower().count("verify with your local") == 1


def test_fallback_messages():
    assert "temporarily unavailable" in guardrails.fallback("api_error")
    assert guardrails.fallback("weird_reason")  # defaults gracefully


def test_i18n_static_and_lang_instruction():
    assert i18n.t("find_button", "pa") != i18n.t("find_button", "en")
    assert "Punjabi" in i18n.lang_instruction("pa")
    assert i18n.t("unknown_key", "en") == "unknown_key"  # graceful fallback

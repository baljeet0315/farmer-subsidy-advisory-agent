"""Unit tests for the confidence engine (pure logic, no network)."""
from __future__ import annotations

from src.confidence import score
from src.models import Confidence


def _m(ok=True, eligible=True):
    return {"ok": ok, "eligible": eligible}


def test_all_agree_eligible_high_confidence():
    outs = {"claude": _m(True, True), "openai": _m(True, True), "gemini": _m(True, True)}
    r = score("pm_kisan", rules_verdict=True, model_outputs=outs)
    assert r.eligible is True
    assert r.confidence == Confidence.HIGH
    assert not r.needs_human_review
    assert r.confidence_score == 1.0


def test_split_vote_is_medium_but_delivered():
    # 2 agree with rules, 1 dissents; majority still matches rules.
    outs = {"claude": _m(True, True), "openai": _m(True, True), "gemini": _m(True, False)}
    r = score("kcc", rules_verdict=True, model_outputs=outs)
    assert r.confidence == Confidence.MEDIUM
    assert not r.needs_human_review


def test_majority_contradicts_rules_flags_review():
    # Rules say eligible, but all models say not eligible -> flag.
    outs = {"claude": _m(True, False), "openai": _m(True, False), "gemini": _m(True, False)}
    r = score("pm_kusum", rules_verdict=True, model_outputs=outs)
    assert r.eligible is True  # delivered verdict still anchored to rules
    assert r.needs_human_review
    assert r.confidence == Confidence.LOW
    assert "disagree" in r.reason.lower()


def test_all_abstain_flags_review():
    outs = {"claude": _m(False), "openai": _m(False), "gemini": {"ok": True, "eligible": "unknown"}}
    r = score("soil_health_card", rules_verdict=True, model_outputs=outs)
    assert r.needs_human_review
    assert r.confidence == Confidence.LOW
    assert r.model_agreement is None


def test_single_model_cannot_be_high():
    # Only one model responds; even full agreement caps at MEDIUM.
    outs = {"claude": _m(True, True), "openai": _m(False), "gemini": {"ok": True, "eligible": "unknown"}}
    r = score("pb_free_power", rules_verdict=True, model_outputs=outs)
    assert r.confidence == Confidence.MEDIUM
    assert not r.needs_human_review


def test_empty_outputs_defers_to_review():
    r = score("pb_crm_subsidy", rules_verdict=True, model_outputs={})
    assert r.needs_human_review
    assert r.confidence == Confidence.LOW
    assert r.confidence_score == 0.0

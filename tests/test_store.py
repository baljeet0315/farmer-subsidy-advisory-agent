"""Tests for the SQLite storage layer (uses a temp DB, no network)."""
from __future__ import annotations

from types import SimpleNamespace

from src import store
from src.models import Category, Confidence, EligibilityResult, FarmerProfile, LandOwnership


def _profile(consent: bool, phone="9876500000"):
    return FarmerProfile(
        farmer_id="web-test", phone=phone, phone_hash=store.hash_phone(phone),
        consent_given=consent, state="Punjab", district="Ludhiana", land_holding_ha=2.0,
        land_ownership=LandOwnership.OWNER, category=Category.GENERAL,
        primary_crop="paddy", irrigation="irrigated",
    )


def _assessed():
    result = EligibilityResult(
        scheme_id="pm_kusum", eligible=True, rules_verdict=True,
        reason="Model majority disagrees with rules; flagged.", confidence=Confidence.LOW,
        confidence_score=0.4, needs_human_review=True, model_agreement=1.0,
    )
    scheme = SimpleNamespace(scheme_name="PM-KUSUM")
    outputs = {"claude": {"eligible": False}, "openai": {"eligible": False}, "gemini": {"eligible": False}}
    return SimpleNamespace(result=result, scheme=scheme, model_outputs=outputs)


def test_consent_controls_raw_phone_storage(tmp_path):
    db = str(tmp_path / "t.db")
    store.save_profile(_profile(consent=True), db_path=db)
    store.save_profile(_profile(consent=False), db_path=db)
    import sqlite3
    rows = sqlite3.connect(db).execute("SELECT phone, phone_hash, consent_given FROM profiles ORDER BY consent_given").fetchall()
    # no-consent row: raw phone is NULL but hash is kept
    no_consent = rows[0]
    assert no_consent[0] is None and no_consent[1] is not None
    # consent row: raw phone stored
    consent = rows[1]
    assert consent[0] == "9876500000"


def test_review_queue_roundtrip(tmp_path):
    db = str(tmp_path / "t.db")
    rid = store.enqueue_review("web-test", store.hash_phone("9876500000"), _assessed(), db_path=db)
    pending = store.list_review_queue("pending", db_path=db)
    assert len(pending) == 1 and pending[0]["scheme_id"] == "pm_kusum"
    assert pending[0]["id"] == rid

    store.resolve_review(rid, "approved", "verified with district office", db_path=db)
    assert store.list_review_queue("pending", db_path=db) == []
    approved = store.list_review_queue("approved", db_path=db)
    assert len(approved) == 1 and approved[0]["reviewer_note"] == "verified with district office"


def test_get_phone_by_hash_respects_consent(tmp_path):
    db = str(tmp_path / "t.db")
    store.save_profile(_profile(consent=True, phone="9111100000"), db_path=db)
    store.save_profile(_profile(consent=False, phone="9222200000"), db_path=db)
    # consented number is recoverable for notification
    assert store.get_phone_by_hash(store.hash_phone("9111100000"), db_path=db) == "9111100000"
    # non-consented number is NOT recoverable
    assert store.get_phone_by_hash(store.hash_phone("9222200000"), db_path=db) is None


def test_log_step_uses_hash(tmp_path):
    db = str(tmp_path / "t.db")
    store.log_step(store.hash_phone("9876500000"), "assessment", {"delivered": 5}, db_path=db)
    import sqlite3
    row = sqlite3.connect(db).execute("SELECT farmer_hash, event FROM logs").fetchone()
    assert row[1] == "assessment"
    assert row[0] == store.hash_phone("9876500000")  # hash, never raw

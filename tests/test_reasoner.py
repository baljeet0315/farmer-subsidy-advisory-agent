"""Tests for the reasoner: JSON parsing + reason_all with mock clients (no network)."""
from __future__ import annotations

from src.llm_clients import MockClient
from src.models import Category, FarmerProfile, LandOwnership, Scheme
from src.reasoner import parse_response, reason_all


def _scheme():
    return Scheme(
        scheme_id="pm_kisan", scheme_name="PM-KISAN", level="national",
        eligibility_rules='{"min_land_ha": 0.01, "land_ownership": ["owner"]}',
        benefit_summary="Rs 6000/year.", documents_required="Aadhaar|Land records",
        application_process="Register online.", where_to_apply="pmkisan.gov.in",
    )


def _profile():
    return FarmerProfile(farmer_id="T", state="Punjab", land_holding_ha=2.0,
                         land_ownership=LandOwnership.OWNER, category=Category.GENERAL,
                         primary_crop="paddy", irrigation="irrigated")


def test_parse_clean_json():
    d = parse_response('{"eligible": true, "explanation": "ok", "documents": ["Aadhaar"], "next_step": "apply", "grounded": true}')
    assert d["eligible"] is True
    assert d["grounded"] is True
    assert not d["parse_error"]


def test_parse_json_with_surrounding_prose():
    d = parse_response('Sure! Here is the answer:\n{"eligible": false, "grounded": true} \nHope that helps.')
    assert d["eligible"] is False
    assert not d["parse_error"]


def test_parse_bad_json_flags_error():
    d = parse_response("this is not json at all")
    assert d["parse_error"]
    assert d["eligible"] == "unknown"


def test_reason_all_three_mock_models():
    good = '{"eligible": true, "explanation": "You own land in Punjab.", "documents": ["Aadhaar"], "next_step": "Register at pmkisan.gov.in", "grounded": true}'
    clients = [MockClient("claude", good), MockClient("openai", good), MockClient("gemini", good)]
    out = reason_all(_profile(), _scheme(), ["PM-KISAN passage text"], clients=clients)
    assert set(out.keys()) == {"claude", "openai", "gemini"}
    assert all(out[m]["ok"] and out[m]["eligible"] is True for m in out)


def test_reason_all_no_clients_returns_empty():
    assert reason_all(_profile(), _scheme(), ["x"], clients=[]) == {}

"""Unit tests for the deterministic rules engine (Punjab knowledge base).

Two layers:
  1. Targeted unit tests for specific rule behaviours and edge cases.
  2. A data-driven test asserting the engine reproduces eval_labeled.csv exactly
     for every demo persona (guards against rule/data drift).
"""
from __future__ import annotations

import csv
import os

import pytest

from src.agent_controller import missing_fields, next_question
from src.models import Category, FarmerProfile, LandOwnership
from src.rules_engine import check, filter_candidates
from src.utils import load_profiles, load_schemes

DATA_DIR = os.environ.get("DATA_DIR", "data")
EVAL_CSV = os.path.join(DATA_DIR, "eval_labeled.csv")


@pytest.fixture(scope="module")
def schemes():
    return load_schemes()


def _scheme(schemes, scheme_id):
    return next(s for s in schemes if s.scheme_id == scheme_id)


def _profile(**kw) -> FarmerProfile:
    base = dict(
        farmer_id="T",
        state="Punjab",
        land_holding_ha=2.0,
        land_ownership=LandOwnership.OWNER,
        category=Category.GENERAL,
        primary_crop="paddy",
        irrigation="irrigated",
    )
    base.update(kw)
    return FarmerProfile(**base)


# --- targeted behaviour tests -------------------------------------------------

def test_owner_paddy_qualifies_for_crop_diversification(schemes):
    res = check(_profile(), _scheme(schemes, "pb_crop_diversification"))
    assert res.passed
    assert "Eligible" in res.reason


def test_wheat_grower_excluded_from_maize_incentive(schemes):
    # Crop diversification (paddy->maize) targets current paddy growers.
    res = check(_profile(primary_crop="wheat"), _scheme(schemes, "pb_crop_diversification"))
    assert not res.passed
    assert "crop" in res.reason


def test_rainfed_owner_excluded_from_free_power(schemes):
    # Free power needs an irrigated (pump-connected) holding.
    res = check(_profile(irrigation="rainfed"), _scheme(schemes, "pb_free_power"))
    assert not res.passed
    assert "irrigation" in res.reason


def test_landless_qualifies_for_nothing(schemes):
    # A landless labourer matches no land-based scheme -> no-match path.
    p = _profile(land_holding_ha=0.0, land_ownership=LandOwnership.SHARECROPPER, irrigation="rainfed")
    assert filter_candidates(p, schemes) == []


def test_tenant_excluded_from_owner_only_schemes(schemes):
    p = _profile(land_ownership=LandOwnership.TENANT, primary_crop="maize")
    elig = {s.scheme_id for s in filter_candidates(p, schemes)}
    # tenant keeps KCC, Soil Health Card, and SDRF relief; loses PM-KISAN & state owner-only schemes
    assert {"kcc", "soil_health_card", "pb_sdrf_crop_relief"} == elig
    assert "pm_kisan" not in elig
    assert "pb_free_power" not in elig


def test_pmfby_absent_from_punjab_kb(schemes):
    # Punjab does not implement PMFBY; it must not be in the knowledge base.
    assert all(s.scheme_id != "pmfby" for s in schemes)


def test_non_punjab_state_excluded_from_state_schemes(schemes):
    p = _profile(state="Haryana")
    elig = {s.scheme_id for s in filter_candidates(p, schemes)}
    assert not any(sid.startswith("pb_") for sid in elig)
    assert "pm_kisan" in elig  # national schemes still apply


def test_missing_land_is_not_determinable(schemes):
    res = check(_profile(land_holding_ha=None), _scheme(schemes, "pm_kisan"))
    assert not res.passed
    assert not res.determinable
    assert "land_holding_ha" in res.missing_info


# --- intake tests -------------------------------------------------------------

def test_missing_fields_detects_gaps():
    p = FarmerProfile(farmer_id="T", land_holding_ha=None, primary_crop=None)
    gaps = missing_fields(p)
    assert "land_holding_ha" in gaps
    assert "primary_crop" in gaps
    assert next_question(p) is not None


def test_complete_profile_has_no_next_question():
    assert next_question(_profile()) is None


def test_landless_zero_is_complete():
    p = _profile(land_holding_ha=0.0)
    assert "land_holding_ha" not in missing_fields(p)


# --- data-driven ground-truth test -------------------------------------------

def _load_eval():
    with open(EVAL_CSV, newline="", encoding="utf-8") as f:
        return {
            r["farmer_id"]: {x for x in r["expected_scheme_ids"].split(";") if x}
            for r in csv.DictReader(f)
        }


def test_engine_matches_eval_ground_truth(schemes):
    profiles = {p.farmer_id: p for p in load_profiles()}
    expected = _load_eval()
    for farmer_id, exp in expected.items():
        got = {s.scheme_id for s in filter_candidates(profiles[farmer_id], schemes)}
        assert got == exp, f"{farmer_id}: got {sorted(got)} expected {sorted(exp)}"

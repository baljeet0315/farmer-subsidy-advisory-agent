"""Agent controller — orchestrates the end-to-end workflow.

Channel-agnostic entry point. Given a (possibly incomplete) FarmerProfile:
intake -> ask missing questions -> rules pass -> retrieval -> dual-LLM
reasoning -> confidence -> route (deliver vs review) -> checklist -> log.

Day 3 implements intake + the rules pass. Retrieval, reasoning, confidence,
and delivery are wired in Days 4-7.
"""
from __future__ import annotations

from .models import ChecklistItem, FarmerProfile
from .rules_engine import RuleCheck, evaluate_all, filter_candidates
from .utils import load_schemes, profile_from_row

# Fields needed before eligibility can be meaningfully assessed. district and
# category are optional (improve precision but not strictly required).
REQUIRED_FIELDS: list[str] = [
    "state",
    "land_holding_ha",
    "land_ownership",
    "primary_crop",
    "irrigation",
]

# Friendly prompts for the conversational (WhatsApp) intake.
FIELD_QUESTIONS: dict[str, str] = {
    "state": "Which state are you farming in?",
    "land_holding_ha": "How much agricultural land do you own or farm, in hectares? (Enter 0 if you are a landless labourer.)",
    "land_ownership": "Do you own the land, rent it as a tenant, or work it as a sharecropper? (owner / tenant / sharecropper)",
    "primary_crop": "What is your main crop? (e.g. paddy, vegetables)",
    "irrigation": "Is your land irrigated or rainfed? (irrigated / rainfed)",
    "category": "What is your social category? (general / sc / st / obc) — optional",
    "district": "Which district are you in? — optional",
}


def missing_fields(profile: FarmerProfile) -> list[str]:
    """Required fields still empty on the profile, in intake order."""
    missing = []
    for field in REQUIRED_FIELDS:
        value = getattr(profile, field, None)
        # land_holding_ha == 0 is a valid answer (landless), so check for None.
        if value is None:
            missing.append(field)
    return missing


def next_question(profile: FarmerProfile) -> str | None:
    """The next intake question to ask, or None when the profile is complete."""
    missing = missing_fields(profile)
    if not missing:
        return None
    return FIELD_QUESTIONS.get(missing[0], f"Please provide your {missing[0]}.")


def build_profile(data: dict) -> FarmerProfile:
    """Construct a FarmerProfile from raw input (form fields or chat slots)."""
    return profile_from_row(data)


def assess(profile: FarmerProfile, schemes: list | None = None) -> list[RuleCheck]:
    """Run the deterministic rules pass over all schemes (Day 3 output)."""
    schemes = schemes if schemes is not None else load_schemes()
    return evaluate_all(profile, schemes)


def run(profile: FarmerProfile) -> list[ChecklistItem]:
    """Full pipeline for a completed profile.

    TODO (Days 4-7): retrieval -> dual-LLM reasoning -> confidence -> routing ->
    checklist. For now this is not yet wired; use assess() for the rules pass.
    """
    raise NotImplementedError("Full pipeline wired across Days 4-7.")

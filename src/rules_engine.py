"""Deterministic eligibility rules engine.

Source of truth for HARD eligibility criteria. Transparent, explainable, and
unit-tested. The two LLMs never override this — disagreement only lowers
confidence and triggers human review.

Rule schema (JSON in scheme.eligibility_rules), all keys optional:
    state          : required state match
    min_land_ha    : land_holding_ha must be >= this
    max_land_ha    : land_holding_ha must be <= this
    land_ownership : allowed ownership values (list)
    primary_crop   : allowed crops, matched as lowercased substrings (list)
    irrigation     : allowed irrigation values (list)
    category        : allowed social categories (list)
    landless       : if true, requires land_holding_ha == 0 (overrides min_land_ha)

check() returns a RuleCheck describing the verdict, a human-readable reason, and
the per-condition breakdown (useful for the explanation + confidence layers).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .models import FarmerProfile, Scheme


@dataclass
class RuleCheck:
    scheme_id: str
    passed: bool
    reason: str
    failed_conditions: list[str] = field(default_factory=list)
    passed_conditions: list[str] = field(default_factory=list)
    missing_info: list[str] = field(default_factory=list)

    @property
    def determinable(self) -> bool:
        """False when a required field was missing, so eligibility is unknown."""
        return not self.missing_info


def _val(profile: FarmerProfile, attr: str):
    v = getattr(profile, attr, None)
    return v.value if hasattr(v, "value") else v


def check(profile: FarmerProfile, scheme: Scheme) -> RuleCheck:
    """Evaluate one scheme's hard criteria against a farmer profile."""
    rules = json.loads(scheme.eligibility_rules)
    passed_c: list[str] = []
    failed_c: list[str] = []
    missing: list[str] = []

    land = profile.land_holding_ha

    # --- land / landless ---
    if rules.get("landless"):
        if land is None:
            missing.append("land_holding_ha")
        elif land == 0:
            passed_c.append("is landless (no agricultural land)")
        else:
            failed_c.append(f"requires landless, but holds {land} ha")
    else:
        if "min_land_ha" in rules:
            if land is None:
                missing.append("land_holding_ha")
            elif land < rules["min_land_ha"]:
                failed_c.append(f"needs land ≥ {rules['min_land_ha']} ha (has {land})")
            else:
                passed_c.append(f"land {land} ha ≥ {rules['min_land_ha']} ha")
        if "max_land_ha" in rules:
            if land is None:
                missing.append("land_holding_ha")
            elif land > rules["max_land_ha"]:
                failed_c.append(f"needs land ≤ {rules['max_land_ha']} ha (has {land})")
            else:
                passed_c.append(f"land {land} ha ≤ {rules['max_land_ha']} ha")

    # --- categorical membership checks ---
    def member_check(rule_key: str, attr: str, label: str):
        if rule_key not in rules:
            return
        allowed = rules[rule_key]
        actual = _val(profile, attr)
        if actual is None:
            missing.append(attr)
        elif attr == "primary_crop":
            if any(c in str(actual).lower() for c in allowed):
                passed_c.append(f"{label} '{actual}' is covered")
            else:
                failed_c.append(f"{label} must be one of {allowed} (has '{actual}')")
        elif actual in allowed:
            passed_c.append(f"{label} '{actual}' is eligible")
        else:
            failed_c.append(f"{label} must be one of {allowed} (has '{actual}')")

    if "state" in rules:
        actual = profile.state
        if not actual:
            missing.append("state")
        elif actual == rules["state"]:
            passed_c.append(f"state is {actual}")
        else:
            failed_c.append(f"requires state {rules['state']} (has '{actual}')")

    member_check("land_ownership", "land_ownership", "land ownership")
    member_check("primary_crop", "primary_crop", "crop")
    member_check("irrigation", "irrigation", "irrigation")
    member_check("category", "category", "category")

    passed = not failed_c and not missing
    if failed_c:
        reason = "Not eligible: " + "; ".join(failed_c)
    elif missing:
        reason = "Need more info to decide: " + ", ".join(sorted(set(missing)))
    else:
        reason = "Eligible: " + "; ".join(passed_c) if passed_c else "Eligible (no hard restrictions)"

    return RuleCheck(
        scheme_id=scheme.scheme_id,
        passed=passed,
        reason=reason,
        failed_conditions=failed_c,
        passed_conditions=passed_c,
        missing_info=sorted(set(missing)),
    )


def filter_candidates(profile: FarmerProfile, schemes: list[Scheme]) -> list[Scheme]:
    """Return schemes whose hard criteria the profile satisfies."""
    return [s for s in schemes if check(profile, s).passed]


def evaluate_all(profile: FarmerProfile, schemes: list[Scheme]) -> list[RuleCheck]:
    """Return the full RuleCheck for every scheme (eligible or not)."""
    return [check(profile, s) for s in schemes]

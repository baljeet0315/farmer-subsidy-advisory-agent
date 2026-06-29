"""Shared helpers: config, logging, and CSV/KB loaders."""
from __future__ import annotations

import csv
import logging
import os
from typing import Optional

from .models import Category, FarmerProfile, LandOwnership, Scheme

# Default data locations (relative to repo root).
DATA_DIR = os.environ.get("DATA_DIR", "data")
SCHEME_CSV = os.path.join(DATA_DIR, "scheme_rules.csv")
PROFILE_CSV = os.path.join(DATA_DIR, "farmer_profile.csv")


def get_logger(name: str = "farmer_agent") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger


def _to_bool(value: str) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "y")


def _to_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_enum(enum_cls, value: str):
    value = (value or "").strip().lower()
    if value == "":
        return None
    try:
        return enum_cls(value)
    except ValueError:
        return None


def load_schemes(path: str = SCHEME_CSV) -> list[Scheme]:
    """Load the scheme knowledge base CSV into Scheme models."""
    schemes: list[Scheme] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            schemes.append(
                Scheme(
                    scheme_id=row["scheme_id"],
                    scheme_name=row["scheme_name"],
                    level=row["level"],
                    eligibility_rules=row["eligibility_rules"],
                    benefit_summary=row["benefit_summary"],
                    documents_required=row["documents_required"],
                    application_process=row["application_process"],
                    where_to_apply=row["where_to_apply"],
                    source_url=row.get("source_url") or None,
                    last_verified=row.get("last_verified") or None,
                    is_synthetic=_to_bool(row.get("is_synthetic", "False")),
                    notes=row.get("notes") or None,
                )
            )
    return schemes


def load_profiles(path: str = PROFILE_CSV) -> list[FarmerProfile]:
    """Load demo/eval farmer profiles CSV into FarmerProfile models."""
    profiles: list[FarmerProfile] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profiles.append(profile_from_row(row))
    return profiles


def profile_from_row(row: dict) -> FarmerProfile:
    """Build a FarmerProfile from a raw dict (CSV row, form, or chat slots)."""
    return FarmerProfile(
        farmer_id=row.get("farmer_id") or "unknown",
        phone_hash=row.get("phone_hash") or None,
        state=row.get("state") or "Chhattisgarh",
        district=row.get("district") or None,
        land_holding_ha=_to_float(row.get("land_holding_ha", "")),
        land_ownership=_to_enum(LandOwnership, row.get("land_ownership", "")),
        category=_to_enum(Category, row.get("category", "")),
        gender=row.get("gender") or None,
        primary_crop=row.get("primary_crop") or None,
        irrigation=row.get("irrigation") or None,
        has_kcc=_to_bool(row["has_kcc"]) if row.get("has_kcc") not in (None, "") else None,
        bank_account=_to_bool(row["bank_account"]) if row.get("bank_account") not in (None, "") else None,
        aadhaar_linked=_to_bool(row["aadhaar_linked"]) if row.get("aadhaar_linked") not in (None, "") else None,
        language=row.get("language") or "hi",
    )

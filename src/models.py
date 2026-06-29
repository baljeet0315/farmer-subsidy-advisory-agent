"""Shared data models (Pydantic).

Defines the canonical, channel-agnostic structures passed between modules:
FarmerProfile (input), Scheme (KB record), EligibilityResult, and the final
ChecklistItem delivered to the farmer.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LandOwnership(str, Enum):
    OWNER = "owner"
    TENANT = "tenant"
    SHARECROPPER = "sharecropper"


class Category(str, Enum):
    GENERAL = "general"
    SC = "sc"
    ST = "st"
    OBC = "obc"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FarmerProfile(BaseModel):
    """Normalized farmer input, produced by any channel (web/WhatsApp/CLI)."""

    farmer_id: str
    phone_hash: Optional[str] = None  # phone is hashed before it reaches here
    state: str = "Chhattisgarh"
    district: Optional[str] = None
    land_holding_ha: Optional[float] = None
    land_ownership: Optional[LandOwnership] = None
    category: Optional[Category] = None
    gender: Optional[str] = None
    primary_crop: Optional[str] = None
    irrigation: Optional[str] = None
    has_kcc: Optional[bool] = None
    bank_account: Optional[bool] = None
    aadhaar_linked: Optional[bool] = None
    language: str = "hi"  # hi | en | cg


class Scheme(BaseModel):
    """One scheme/advisory record from the knowledge base."""

    scheme_id: str
    scheme_name: str
    level: str  # national | state
    eligibility_rules: str  # machine-checkable expression / structured rule
    benefit_summary: str
    documents_required: str
    application_process: str
    where_to_apply: str
    source_url: Optional[str] = None
    last_verified: Optional[str] = None
    is_synthetic: bool = False
    notes: Optional[str] = None


class EligibilityResult(BaseModel):
    """Outcome for a single scheme after rules + dual-LLM reasoning."""

    scheme_id: str
    eligible: bool
    rules_verdict: bool
    reason: str
    confidence: Confidence
    confidence_score: float = Field(ge=0.0, le=1.0)
    needs_human_review: bool = False
    model_agreement: Optional[float] = None  # claude vs openai


class ChecklistItem(BaseModel):
    """Farmer-facing, plain-language action item for one eligible scheme."""

    scheme_name: str
    what_you_get: str
    documents_needed: list[str]
    next_step: str
    confidence: Confidence
    note: str = "This is guidance — please verify with your local agriculture office / CSC."

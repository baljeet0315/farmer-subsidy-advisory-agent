"""Agent controller — orchestrates the end-to-end workflow.

Channel-agnostic entry point. Given a (possibly incomplete) FarmerProfile:
intake -> ask missing questions -> rules pass -> retrieval -> dual-LLM
reasoning -> confidence -> route (deliver vs review) -> checklist -> log.

Day 3 implements intake + the rules pass. Retrieval, reasoning, confidence,
and delivery are wired in Days 4-7.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import confidence, reasoner
from .llm_clients import LLMClient, get_default_clients
from .models import ChecklistItem, EligibilityResult, FarmerProfile, Scheme
from .retriever import retrieve
from .rules_engine import RuleCheck, check, evaluate_all, filter_candidates
from .utils import load_schemes, profile_from_row

NO_INFO_MSG = (
    "I couldn't find relevant information about that in the scheme documents. "
    "Please ask about the farmer schemes you're eligible for, or verify with your "
    "local agriculture office / CSC."
)
# Chroma cosine distance above which a retrieved passage is treated as irrelevant.
RELEVANCE_MAX_DISTANCE = 1.35

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
    # Collected on the web form (with consent). Stored raw + hashed; not used for
    # eligibility. WhatsApp already knows the sender's number.
    "phone": "Your mobile number (optional) — we store it only with your consent to help you follow up.",
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


@dataclass
class AssessedScheme:
    """One scheme fully assessed: rules + 3-LLM cross-check + confidence + output."""

    scheme: Scheme
    rules_check: RuleCheck
    result: EligibilityResult
    checklist_item: ChecklistItem
    model_outputs: dict


def _checklist_item(scheme: Scheme, result: EligibilityResult, model_outputs: dict) -> ChecklistItem:
    """Build the farmer-facing card. Benefit/documents come from the authoritative
    KB; the plain-language 'why' prefers a grounded model explanation."""
    explanation = ""
    for out in model_outputs.values():
        if out.get("ok") and out.get("grounded") and out.get("explanation"):
            explanation = out["explanation"]
            break
    what = scheme.benefit_summary
    if explanation:
        what = f"{scheme.benefit_summary}  (Why you qualify: {explanation})"
    return ChecklistItem(
        scheme_name=scheme.scheme_name,
        what_you_get=what,
        documents_needed=[d.strip() for d in scheme.documents_required.split("|")],
        next_step=f"{scheme.application_process}  Apply at: {scheme.where_to_apply}",
        confidence=result.confidence,
    )


def _retrieval_query(profile: FarmerProfile, scheme: Scheme) -> str:
    return f"{scheme.scheme_name} eligibility documents benefit for {profile.primary_crop} farmer"


def assess_with_llms(profile: FarmerProfile, clients: list[LLMClient] | None = None,
                     schemes: list[Scheme] | None = None, k: int = 3) -> list[AssessedScheme]:
    """Full eligibility pipeline for the schemes the rules engine passes.

    For each rules-eligible scheme: retrieve passages -> three LLMs judge
    independently -> confidence + routing. (We reason about rules-positive
    schemes — the recommendations we're about to deliver.)
    """
    schemes = schemes if schemes is not None else load_schemes()
    clients = clients if clients is not None else get_default_clients()
    assessed: list[AssessedScheme] = []
    for scheme in schemes:
        rc = check(profile, scheme)
        if not rc.passed:
            continue
        passages = [p["text"] for p in retrieve(_retrieval_query(profile, scheme),
                                                 scheme_ids=[scheme.scheme_id], k=k)]
        model_outputs = reasoner.reason_all(profile, scheme, passages, clients=clients)
        result = confidence.score(scheme.scheme_id, rc.passed, model_outputs)
        item = _checklist_item(scheme, result, model_outputs)
        assessed.append(AssessedScheme(scheme, rc, result, item, model_outputs))
    return assessed


def run(profile: FarmerProfile, clients: list[LLMClient] | None = None) -> dict:
    """Deliverable split for the UI: auto-delivered vs flagged-for-review."""
    assessed = assess_with_llms(profile, clients=clients)
    return {
        "delivered": [a for a in assessed if not a.result.needs_human_review],
        "flagged": [a for a in assessed if a.result.needs_human_review],
        "all": assessed,
    }


# --- grounded follow-up chat (scoped to the farmer's eligible schemes) --------

FOLLOWUP_SYSTEM = (
    "You are a helpful assistant answering a Punjab farmer's follow-up questions "
    "about specific government schemes. Rules: answer ONLY from the provided "
    "scheme passages; never use outside knowledge or invent details; if the "
    "passages don't cover the question, say you don't have that information and "
    "suggest verifying locally; stay strictly on the topic of these schemes. "
    "Keep answers short and plain. Always remind the farmer this is guidance to "
    "verify with their local agriculture office / CSC."
)


def answer_followup(profile: FarmerProfile, question: str, eligible_scheme_ids: list[str],
                    clients: list[LLMClient] | None = None, k: int = 4) -> str:
    """Answer a follow-up strictly from RAG passages scoped to eligible schemes.

    Out-of-scope / no relevant passage -> polite NO_INFO_MSG (never a guess).
    """
    hits = retrieve(question, scheme_ids=eligible_scheme_ids or None, k=k)
    relevant = [h for h in hits if h["distance"] <= RELEVANCE_MAX_DISTANCE]
    if not relevant:
        return NO_INFO_MSG

    clients = clients if clients is not None else get_default_clients()
    if not clients:
        return NO_INFO_MSG
    passages = "\n---\n".join(h["text"] for h in relevant)
    user = f"SCHEME PASSAGES:\n{passages}\n\nFARMER QUESTION: {question}\n\nAnswer from the passages only."
    res = clients[0].complete(FOLLOWUP_SYSTEM, user)
    return res.text if res.ok and res.text else NO_INFO_MSG

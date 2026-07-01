"""Three-LLM reasoning layer (Claude + OpenAI + Gemini).

Each model INDEPENDENTLY judges whether the farmer is eligible for one scheme,
grounded strictly in the retrieved passages, and explains in plain language. The
models are NOT told the rules-engine verdict — keeping them independent is what
makes the cross-check (in confidence.py) meaningful.

Roles: a SYSTEM message carries the scope + grounding rules; a USER message
carries the profile + scheme + retrieved passages. Output is strict JSON.

Grounding: the system prompt forbids using outside knowledge; if the passages
don't support a decision, the model returns eligible="unknown" and grounded is
set accordingly. See guardrails.py (Day 8) for the verification pass.
"""
from __future__ import annotations

import concurrent.futures
import json
import re

from . import i18n
from .llm_clients import LLMClient, get_default_clients
from .models import FarmerProfile, Scheme

SYSTEM_PROMPT = (
    "You are a careful assistant that helps Indian (Punjab) farmers understand "
    "government agriculture schemes. Follow these rules strictly:\n"
    "1. Use ONLY the information in the provided scheme passages. Do not use any "
    "outside knowledge or invent scheme details.\n"
    "2. Decide if THIS farmer is eligible for THIS scheme based on their profile "
    "and the passages.\n"
    "3. If the passages do not contain enough information to decide, set "
    '"eligible" to "unknown".\n'
    "4. Keep the explanation short, plain, and farmer-friendly.\n"
    "5. Respond with ONLY a JSON object, no prose before or after, in exactly "
    "this shape:\n"
    '{"eligible": true|false|"unknown", "explanation": "1-2 sentences", '
    '"documents": ["..."], "next_step": "one short sentence", '
    '"grounded": true|false}\n'
    '"grounded" must be false if you relied on anything not in the passages.'
)


def build_user_prompt(profile: FarmerProfile, scheme: Scheme, passages: list[str]) -> str:
    prof = (
        f"State: {profile.state}\n"
        f"District: {profile.district or 'n/a'}\n"
        f"Land holding (ha): {profile.land_holding_ha}\n"
        f"Land ownership: {getattr(profile.land_ownership, 'value', profile.land_ownership)}\n"
        f"Category: {getattr(profile.category, 'value', profile.category)}\n"
        f"Primary crop: {profile.primary_crop}\n"
        f"Irrigation: {profile.irrigation}\n"
        f"Already has KCC: {profile.has_kcc}\n"
    )
    joined = "\n---\n".join(passages) if passages else "(no passages retrieved)"
    lang = i18n.lang_instruction(getattr(profile, "language", "en"))
    return (
        f"SCHEME: {scheme.scheme_name}\n\n"
        f"FARMER PROFILE:\n{prof}\n"
        f"SCHEME PASSAGES (your only source of truth):\n{joined}\n\n"
        "Is this farmer eligible for this scheme? Respond with the JSON object only."
        f"{lang}"
    )


def parse_response(text: str) -> dict:
    """Extract the JSON object from a model response, tolerating stray prose."""
    if not text:
        return {"eligible": "unknown", "explanation": "", "documents": [],
                "next_step": "", "grounded": False, "parse_error": True}
    match = re.search(r"\{.*\}", text, re.DOTALL)
    raw = match.group(0) if match else text
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"eligible": "unknown", "explanation": text[:200], "documents": [],
                "next_step": "", "grounded": False, "parse_error": True}
    # normalise
    data.setdefault("eligible", "unknown")
    data.setdefault("explanation", "")
    data.setdefault("documents", [])
    data.setdefault("next_step", "")
    data.setdefault("grounded", False)
    data["parse_error"] = False
    return data


def reason_one(client: LLMClient, profile: FarmerProfile, scheme: Scheme,
               passages: list[str]) -> dict:
    """Run one model and parse its output. Records ok/abstain + raw for auditing."""
    user = build_user_prompt(profile, scheme, passages)
    result = client.complete(SYSTEM_PROMPT, user)
    if not result.ok:
        return {"model": client.name, "ok": False, "error": result.error,
                "eligible": "unknown", "explanation": "", "documents": [],
                "next_step": "", "grounded": False}
    parsed = parse_response(result.text)
    parsed.update({"model": client.name, "ok": True, "raw": result.text})
    return parsed


def reason_all(profile: FarmerProfile, scheme: Scheme, passages: list[str],
               clients: list[LLMClient] | None = None) -> dict[str, dict]:
    """Run all models concurrently. Returns {model_name: parsed_output}."""
    clients = clients if clients is not None else get_default_clients()
    if not clients:
        return {}
    out: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(clients)) as ex:
        futures = {ex.submit(reason_one, c, profile, scheme, passages): c for c in clients}
        for fut in concurrent.futures.as_completed(futures):
            r = fut.result()
            out[r["model"]] = r
    return out

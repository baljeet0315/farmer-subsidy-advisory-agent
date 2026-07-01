"""Live three-LLM pipeline check — run this on your machine (needs API keys).

Loads .env, runs the full rules -> retrieval -> 3-LLM -> confidence pipeline for
a sample Punjab farmer, and prints each model's independent vote + the confidence
verdict. Also probes the grounded follow-up chat and an out-of-scope question.

    python -m eval.try_llm            # uses demo persona P001
    python -m eval.try_llm P006       # any farmer_id from data/farmer_profile.csv

Requires: pip install -r requirements.txt, keys in .env, and the index built
(`python -m src.retriever build`).
"""
from __future__ import annotations

import sys

from dotenv import load_dotenv

load_dotenv()  # pull ANTHROPIC/OPENAI/GEMINI keys from .env

from src import agent_controller as ac  # noqa: E402
from src.llm_clients import get_default_clients  # noqa: E402
from src.utils import load_profiles  # noqa: E402


def main():
    clients = get_default_clients()
    print(f"Active models: {[c.name for c in clients] or 'NONE — check your .env keys'}\n")
    if not clients:
        return

    fid = sys.argv[1] if len(sys.argv) > 1 else "P001"
    profiles = {p.farmer_id: p for p in load_profiles()}
    if fid not in profiles:
        print(f"Unknown farmer_id {fid}. Options: {list(profiles)}")
        return
    profile = profiles[fid]
    print(f"Farmer {fid}: {profile.district}, {profile.land_holding_ha}ha, "
          f"{profile.land_ownership.value}, {profile.primary_crop}, {profile.irrigation}\n")

    out = ac.run(profile, clients=clients)
    print(f"DELIVERED (auto): {len(out['delivered'])}   FLAGGED (human review): {len(out['flagged'])}\n")

    for a in out["all"]:
        r = a.result
        votes = {m: o.get("eligible") for m, o in a.model_outputs.items()}
        flag = "  ⚠ REVIEW" if r.needs_human_review else ""
        print(f"● {a.scheme.scheme_id:24} conf={r.confidence.value:6} "
              f"score={r.confidence_score}  votes={votes}{flag}")

    print("\n--- grounded follow-up ---")
    eligible_ids = [a.scheme.scheme_id for a in out["all"]]
    print("Q: What documents do I need for the solar pump scheme?")
    print("A:", ac.answer_followup(profile, "What documents do I need for the solar pump scheme?",
                                    eligible_ids, clients=clients), "\n")
    print("Q (out of scope): What's the weather tomorrow?")
    print("A:", ac.answer_followup(profile, "What's the weather tomorrow?", eligible_ids, clients=clients))


if __name__ == "__main__":
    main()

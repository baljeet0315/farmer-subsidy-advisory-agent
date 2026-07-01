"""WhatsApp channel — Twilio webhook (FastAPI).

Conversational intake over WhatsApp: greets, asks for the farm details one at a
time, runs the same agent pipeline, replies with the checklist, then answers
follow-up questions (grounded). Low-confidence schemes are flagged into the same
reviewer queue as the web app.

Deploy (Day 8): run behind a public URL (Railway) and point the Twilio WhatsApp
sandbox 'When a message comes in' webhook at POST /webhook.

    uvicorn app.whatsapp_webhook:app --reload      # local
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Response

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import agent_controller as ac, store  # noqa: E402
from src.llm_clients import get_default_clients  # noqa: E402
from src.utils import profile_from_row  # noqa: E402

app = FastAPI(title="Farmer Agent WhatsApp Webhook")

# In-memory session per sender (resets on restart — fine for the demo).
_sessions: dict[str, dict] = {}

# Ordered intake with a validator + prompt for each field.
FIELDS = [
    ("land_holding_ha", "How much land do you farm, in hectares? (e.g. 2, or 0 if landless)"),
    ("land_ownership", "Do you own, rent (tenant), or sharecrop the land? Reply: owner / tenant / sharecropper"),
    ("primary_crop", "What is your main crop? (e.g. paddy, wheat, cotton, maize)"),
    ("irrigation", "Is your land irrigated or rainfed? Reply: irrigated / rainfed"),
]


def _valid(field: str, value: str) -> bool:
    v = value.strip().lower()
    if field == "land_holding_ha":
        try:
            float(v)
            return True
        except ValueError:
            return False
    if field == "land_ownership":
        return v in ("owner", "tenant", "sharecropper")
    if field == "irrigation":
        return v in ("irrigated", "rainfed")
    return bool(v)


def _twiml(text: str) -> Response:
    from twilio.twiml.messaging_response import MessagingResponse

    r = MessagingResponse()
    r.message(text)
    return Response(content=str(r), media_type="application/xml")


def _summary(out: dict) -> str:
    if not out["all"]:
        return ("Based on your details, no schemes matched. Please check with your local "
                "agriculture office / CSC. Reply 'restart' to try again.")
    lines = [f"✅ You may qualify for {len(out['all'])} scheme(s):"]
    for i, a in enumerate(out["all"], 1):
        badge = {"high": "", "medium": " (medium confidence)",
                 "low": " ⚠ provisional, under review"}.get(a.result.confidence.value, "")
        lines.append(f"{i}. {a.scheme.scheme_name}{badge}")
    lines.append("\nAsk me any question about these schemes, or reply 'restart'. "
                 "Guidance only — verify with your local office / CSC.")
    return "\n".join(lines)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/webhook")
def webhook(From: str = Form(""), Body: str = Form("")):
    sender = From
    text = (Body or "").strip()
    sess = _sessions.get(sender)

    if text.lower() in ("restart", "reset") or sess is None:
        _sessions[sender] = {"stage": "intake", "idx": 0, "data": {}}
        return _twiml("🌾 Namaste! I can help you find Punjab farmer schemes you may "
                      "qualify for.\n\n" + FIELDS[0][1])

    if sess["stage"] == "intake":
        field, _ = FIELDS[sess["idx"]]
        if not _valid(field, text):
            return _twiml(f"Sorry, I didn't get that.\n\n{FIELDS[sess['idx']][1]}")
        sess["data"][field] = text.strip().lower()
        sess["idx"] += 1
        if sess["idx"] < len(FIELDS):
            return _twiml(FIELDS[sess["idx"]][1])
        # intake complete -> run pipeline
        number = sender.replace("whatsapp:", "")
        row = dict(sess["data"], state="Punjab", farmer_id=f"wa-{abs(hash(sender)) % 100000}",
                   phone=number)
        profile = profile_from_row(row)
        profile.phone_hash = store.hash_phone(number)
        profile.consent_given = True  # messaging us on WhatsApp implies consent to follow up
        clients = get_default_clients()
        out = ac.run(profile, clients=clients)
        store.save_profile(profile)
        store.log_step(profile.phone_hash, "assessment_whatsapp",
                       {"delivered": len(out["delivered"]), "flagged": len(out["flagged"])})
        for a in out["flagged"]:
            store.enqueue_review(profile.farmer_id, profile.phone_hash, a)
        sess.update(stage="chat", profile=profile,
                    eligible_ids=[a.scheme.scheme_id for a in out["all"]])
        return _twiml(_summary(out))

    # chat stage -> grounded follow-up
    ans = ac.answer_followup(sess["profile"], text, sess.get("eligible_ids", []),
                             clients=get_default_clients())
    return _twiml(ans)

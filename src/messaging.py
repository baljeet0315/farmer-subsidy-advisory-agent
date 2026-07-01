"""Outbound WhatsApp messaging via Twilio (used by the reviewer notify flow).

Lazy-imports the Twilio SDK and reads credentials from .env. Returns a status
dict rather than raising, so a missing/invalid config degrades gracefully.
"""
from __future__ import annotations

import os


def send_whatsapp(to_number: str, body: str) -> dict:
    """Send a WhatsApp message. `to_number` is a plain phone number (e.g. +9198...).

    Returns {"ok": bool, "sid"/"error": ...}. No-ops gracefully if unconfigured.
    """
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not (sid and token and to_number):
        return {"ok": False, "error": "Twilio not configured or missing recipient"}
    try:
        from twilio.rest import Client

        to = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"
        msg = Client(sid, token).messages.create(from_=from_, to=to, body=body)
        return {"ok": True, "sid": msg.sid}
    except Exception as e:
        return {"ok": False, "error": str(e)}

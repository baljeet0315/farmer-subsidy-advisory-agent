"""WhatsApp channel — Twilio webhook (FastAPI).

Receives inbound WhatsApp messages, drives the conversational intake, calls the
agent controller, and replies with the checklist. Deployed to a free cloud host
(Render/Railway) so the bot is always-on.

TODO (Day 8): /webhook endpoint -> session state -> agent_controller -> reply.
"""

from fastapi import FastAPI

app = FastAPI(title="Farmer Agent WhatsApp Webhook")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# TODO: @app.post("/webhook") Twilio inbound handler.

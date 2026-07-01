"""Tests for the messaging helper (no network — checks graceful degradation)."""
from __future__ import annotations

from src import messaging


def test_send_whatsapp_unconfigured_is_graceful(monkeypatch):
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    res = messaging.send_whatsapp("+919000000000", "hi")
    assert res["ok"] is False
    assert "error" in res


def test_send_whatsapp_missing_recipient(monkeypatch):
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "x")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "y")
    res = messaging.send_whatsapp("", "hi")
    assert res["ok"] is False

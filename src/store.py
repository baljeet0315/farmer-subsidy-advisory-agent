"""Storage, privacy, and logging (SQLite).

Persists profiles, the review queue, and anonymized step logs. Phone numbers
are hashed (PHONE_HASH_SALT) before storage — minimal personal data is kept.

TODO (Day 6):
- hash_phone(phone) -> str
- init_db(), save_profile(), enqueue_review(), list_review_queue()
- log_step(event) for the agent step log used in evaluation
"""
from __future__ import annotations

import hashlib
import os


def hash_phone(phone: str) -> str:
    """Salted hash of a phone number for privacy-safe logging."""
    salt = os.getenv("PHONE_HASH_SALT", "change-me")
    return hashlib.sha256((salt + phone).encode()).hexdigest()[:16]


def init_db() -> None:
    """Create tables if absent. TODO: implement."""
    raise NotImplementedError

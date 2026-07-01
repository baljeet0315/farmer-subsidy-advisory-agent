"""Storage, privacy, and logging (SQLite).

Persists profiles, the review queue, and step logs.

Phone-number handling (per project decision):
- The RAW number is stored WITH the farmer's consent (consent_given) so future
  features (outreach, cross-channel sync) remain possible.
- A salted hash (hash_phone / PHONE_HASH_SALT) is ALSO stored as the stable
  identity/join key, and is what appears in LOGS — logs never contain the raw
  number.
See FUTURE_FEATURES.md for the deferred cross-channel sync that reuses phone_hash.

TODO (Day 6):
- hash_phone(phone) -> str   [implemented below]
- init_db(), save_profile(profile)  # stores raw phone + phone_hash + consent
- enqueue_review(), list_review_queue()
- log_step(event)  # uses phone_hash only, never the raw number
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

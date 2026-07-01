"""Storage, privacy, and logging (SQLite).

Persists profiles, the review queue, and step logs.

Phone-number handling (per project decision):
- The RAW number is stored WITH the farmer's consent (consent_given) so future
  features (outreach, cross-channel sync) remain possible.
- A salted hash (hash_phone / PHONE_HASH_SALT) is ALSO stored as the stable
  identity/join key, and is what appears in LOGS — logs never contain the raw
  number.
See FUTURE_FEATURES.md for the deferred cross-channel sync that reuses phone_hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "data/app.db")


def hash_phone(phone: str) -> str:
    """Salted hash of a phone number — used as identity key and in logs."""
    salt = os.getenv("PHONE_HASH_SALT", "change-me")
    return hashlib.sha256((salt + (phone or "")).encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _conn(db_path: str | None = None):
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Create tables if absent."""
    with _conn(db_path) as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                farmer_id TEXT,
                phone TEXT,               -- raw, stored only with consent
                phone_hash TEXT,          -- identity key
                consent_given INTEGER,
                state TEXT, district TEXT,
                land_holding_ha REAL, land_ownership TEXT,
                category TEXT, gender TEXT,
                primary_crop TEXT, irrigation TEXT, has_kcc INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS review_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id TEXT, phone_hash TEXT,
                scheme_id TEXT, scheme_name TEXT,
                rules_verdict INTEGER,
                confidence TEXT, confidence_score REAL,
                reason TEXT, model_votes TEXT,
                status TEXT DEFAULT 'pending',   -- pending | approved | edited
                reviewer_note TEXT,
                created_at TEXT, decided_at TEXT
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_hash TEXT,        -- never the raw number
                event TEXT, detail TEXT, created_at TEXT
            );
            """
        )


def save_profile(profile, db_path: str | None = None) -> None:
    """Persist a farmer profile: raw phone (with consent) + hash + fields."""
    init_db(db_path)
    raw = profile.phone if profile.consent_given else None
    phash = profile.phone_hash or (hash_phone(profile.phone) if profile.phone else None)
    with _conn(db_path) as c:
        c.execute(
            """INSERT INTO profiles (farmer_id, phone, phone_hash, consent_given, state,
               district, land_holding_ha, land_ownership, category, gender, primary_crop,
               irrigation, has_kcc, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (profile.farmer_id, raw, phash, int(bool(profile.consent_given)), profile.state,
             profile.district, profile.land_holding_ha,
             getattr(profile.land_ownership, "value", profile.land_ownership),
             getattr(profile.category, "value", profile.category), profile.gender,
             profile.primary_crop, profile.irrigation,
             None if profile.has_kcc is None else int(profile.has_kcc), _now()),
        )


def enqueue_review(farmer_id: str, phone_hash: str | None, assessed, db_path: str | None = None) -> int:
    """Add one flagged (low-confidence) scheme result to the reviewer queue."""
    init_db(db_path)
    r = assessed.result
    votes = {m: o.get("eligible") for m, o in assessed.model_outputs.items()}
    with _conn(db_path) as c:
        cur = c.execute(
            """INSERT INTO review_queue (farmer_id, phone_hash, scheme_id, scheme_name,
               rules_verdict, confidence, confidence_score, reason, model_votes,
               status, created_at)
               VALUES (?,?,?,?,?,?,?,?,?, 'pending', ?)""",
            (farmer_id, phone_hash, r.scheme_id, assessed.scheme.scheme_name,
             int(r.rules_verdict), r.confidence.value, r.confidence_score, r.reason,
             json.dumps(votes), _now()),
        )
        return cur.lastrowid


def list_review_queue(status: str = "pending", db_path: str | None = None) -> list[dict]:
    init_db(db_path)
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT * FROM review_queue WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_review(review_id: int, status: str, note: str = "", db_path: str | None = None) -> None:
    """Mark a queued case approved or edited by the reviewer."""
    with _conn(db_path) as c:
        c.execute(
            "UPDATE review_queue SET status = ?, reviewer_note = ?, decided_at = ? WHERE id = ?",
            (status, note, _now(), review_id),
        )


def get_phone_by_hash(phone_hash: str, db_path: str | None = None) -> str | None:
    """Return the raw phone for a hash IF it was stored with consent, else None.
    Used to notify a farmer of a reviewed result on WhatsApp."""
    if not phone_hash:
        return None
    init_db(db_path)
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT phone FROM profiles WHERE phone_hash = ? AND consent_given = 1 "
            "AND phone IS NOT NULL ORDER BY created_at DESC LIMIT 1",
            (phone_hash,),
        ).fetchone()
        return row["phone"] if row else None


def log_step(farmer_hash: str | None, event: str, detail: dict | None = None, db_path: str | None = None) -> None:
    """Append an audit log entry. Uses the phone hash, never the raw number."""
    init_db(db_path)
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO logs (farmer_hash, event, detail, created_at) VALUES (?,?,?,?)",
            (farmer_hash, event, json.dumps(detail or {}), _now()),
        )

# Future Features & Ideas

A running backlog of enhancements considered but intentionally **out of scope for
the current build**. Kept here so the vision isn't lost. Not committed to the
10-day plan unless promoted.

---

## 1. Cross-channel conversation sync (web chatbox ↔ WhatsApp)

**Idea.** A farmer's conversation and profile follow them across channels: start
on the web chatbox, continue later on WhatsApp (or vice-versa), and the agent
already "knows" them — same profile, same chat history.

**Why deferred.** Decided (Day 4) to keep the web and WhatsApp channels
**independent** for now to reduce scope and avoid the identity-verification
complexity below. Documented here as a planned future feature.

**Note:** the web form *does* now collect + store the phone number (raw + salted
hash, with consent) so the data is ready when this feature is built — only the
sync wiring and OTP verification remain.

**How it would work.**
- **Shared identity key:** the phone number, hashed (`store.hash_phone`), is the
  join key. Same number → same hash → same record. WhatsApp provides the number
  directly; the web form would collect it.
- **Conversation store:** a `conversations` table (SQLite or Supabase Postgres)
  keyed by `phone_hash`, holding the profile snapshot + message history +
  eligible-scheme results. Both channels read/write the same record.
- **Privacy:** never store the plaintext number — the salted hash is the join
  key, so sync works entirely on hashes (consistent with the project's
  privacy-conscious design).

**Identity verification (the catch).** Trusting a typed phone number lets a user
pull up someone else's data. Production hardening = send a one-time OTP (via
WhatsApp/SMS) to verify ownership before syncing. Needs SMS/WhatsApp send wired
up early, which is why it's deferred.

**Architecture already anticipates this:** `FarmerProfile.phone_hash` and
`store.hash_phone()` exist (currently unused), so wiring this later is additive,
not a rewrite.

---

<!-- Add new future ideas below this line, newest first. -->

## 3. UI/UX polish (farmer app + reviewer dashboard)

**Idea.** The current Streamlit UI is functional but plain. Planned refinements
(to be detailed): visual branding/theme, cleaner card layout, Punjabi UI labels
(not just answer language), mobile-friendly layout, progress/loading states, and
possibly a more guided step-by-step intake.

**Why deferred.** Day 7 focused on a working end-to-end UI. Cosmetic/UX changes
are lower risk and can be layered on once the pipeline is locked. Add specific
change requests here as they come up.

## 2. Persist follow-up chat across return visits

**Idea.** Remember a farmer's past chatbox conversation when they come back later
(not just within one session).

**Why deferred.** Current build uses **session-only** chat memory (Streamlit
session state), which resets when the tab closes. Cross-visit persistence needs a
per-farmer conversation store and overlaps the cross-channel sync above (same
`phone_hash` key + storage). Bundle it with feature #1 when built.

# Farmer Subsidy & Advisory Navigation Agent — Project Vision & Specification

**Author:** B
**Status:** Planning / awaiting approval
**Date:** 2026-06-29
**Track:** AAI · Domain: Agriculture scheme navigation · Mode: Solo · Duration: ~10 days

> This is the north-star document. Nothing gets built until this is approved. Edit anything that doesn't match your intent.

---

## 1. Vision in one paragraph

A small-farm owner in Punjab sends a WhatsApp message (or opens a web form), answers a few simple questions about their land, crop, and category, and gets back a clear, plain-language checklist of the government schemes and advisories they actually qualify for — what each gives them, the documents they need, and the next concrete step to claim it. Behind the scenes, three different LLMs (Claude, OpenAI, Gemini) independently reason about eligibility, a deterministic rules engine checks the hard criteria, and the system measures how much they agree via majority vote. High agreement is delivered automatically; a split or a majority that contradicts the rules is flagged and routed to a human reviewer before anything goes to the farmer. The farmer stays informed; humans stay in control of the sensitive calls.

---

## 2. The problem & who it's for

**Problem.** India runs dozens of overlapping farmer support schemes (national + state). Eligibility rules are buried in PDFs and circulars, written in bureaucratic language, and farmers often don't know what applies to them or how to claim it. The cost of *not* knowing is real money and missed support.

**Primary user.** A smallholder paddy/wheat farmer in Punjab (or someone helping them — a family member, a CSC/Common Service Centre operator, an agri-officer).

**Secondary user.** A reviewer/agri-officer who handles flagged, low-confidence cases.

**Why an agent, not a website.** Schemes change, eligibility is multi-factor and conditional, and answers need to be *explained*, not just listed. That's exactly where retrieval + reasoning + guardrails earn their place.

---

## 3. Locked decisions (from planning Q&A)

| Area | Decision |
|---|---|
| Ambition | Meaningfully beyond the minimum — portfolio-grade |
| Region | India national schemes **+ Punjab** state schemes |
| LLMs | **Three-model ensemble: Claude + OpenAI + Gemini** with a majority-vote confidence signal |
| Eligibility logic | **Hybrid**: deterministic rules engine + RAG + LLM explanation |
| Scheme coverage | **8–12 schemes, deep & accurate** (quality over quantity) |
| Languages | **Punjabi + English** (both reliable) |
| Confidence score | **Display to user + auto-route low-confidence to human** |
| Human handoff | **Reviewer dashboard + queue** (Streamlit admin page) |
| Channels | **Streamlit web app** (primary/demo) + **WhatsApp via Twilio** + **CLI** (for eval) |
| WhatsApp hosting | **Free cloud host (Render/Railway)** so the bot is always-on |
| Data strategy | **Curated real scheme data + clearly-labeled synthetic fill** |
| Privacy | **Privacy-conscious**: hash/anonymize phone numbers, minimal storage |
| Evaluation | **Both**: labeled test-case suite w/ metrics **+** narrated scenario walkthroughs |
| Timeline | ~10 days, steady pace |

---

## 4. The differentiators (our "extra mile")

These are what lift this above a typical submission:

1. **Three-LLM cross-verification with a real confidence score.** Majority vote across Claude/OpenAI/Gemini — not decoration; it drives the guardrail.
2. **Confidence-gated human-in-the-loop.** Low agreement → reviewer queue → approve/edit → deliver. This *is* the responsible-AI story the brief asks for.
3. **Hybrid eligibility** — auditable deterministic rules for hard facts, LLM only for retrieval-grounded explanation. Defensible in a sensitive domain.
4. **Multi-channel, channel-agnostic core** — same agent serves web + WhatsApp.
5. **Trilingual, farmer-friendly output** with honest scope limits.
6. **Rigorous eval** — precision/recall over labeled profiles + model-agreement stats.

---

## 5. System architecture

```
                        ┌──────────────────────────────┐
        Channels        │   Streamlit web │ WhatsApp(Twilio) │ CLI   │
                        └───────────────┬──────────────┘
                                        │  (normalized FarmerProfile)
                                        ▼
                            ┌───────────────────────┐
                            │     Agent Controller   │  ← orchestration, missing-field
                            └───────────┬───────────┘     follow-up questions, state
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
        ┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
        │ Rules Engine    │   │  RAG Retriever    │   │  Two-LLM Reasoner │
        │ (hard criteria) │   │ (scheme KB +      │   │  Claude + OpenAI  │
        │ deterministic   │   │  vector store)    │   │  parallel calls   │
        └───────┬────────┘   └─────────┬────────┘   └─────────┬────────┘
                └──────────────┬───────┴───────────────┬──────┘
                               ▼                        ▼
                     ┌──────────────────┐    ┌────────────────────┐
                     │ Confidence Engine │◄──│ agreement(model↔model│
                     │  score + routing  │    │ , model↔rules)      │
                     └─────────┬────────┘    └────────────────────┘
                  high conf │            │ low conf
                            ▼            ▼
                  ┌──────────────┐   ┌─────────────────────┐
                  │ Deliver      │   │ Reviewer Queue/Dash │ → approve/edit → deliver
                  │ checklist    │   └─────────────────────┘
                  └──────┬───────┘
                         ▼
                  ┌──────────────────────────────┐
                  │ Structured output + Logs/Eval │  (anonymized)
                  └──────────────────────────────┘
```

---

## 6. Core workflow (happy path)

1. **Intake.** User starts on a channel. Agent collects a `FarmerProfile` (form on web; conversational Q&A on WhatsApp).
2. **Completeness check.** Agent asks follow-up questions only for missing fields needed by candidate schemes.
3. **Rules pass.** Deterministic engine filters schemes by hard criteria (land size, category, crop, residency, etc.) → candidate set + reason codes.
4. **Retrieval.** RAG pulls the relevant scheme passages (benefits, documents, process) for the candidate set.
5. **Dual reasoning.** Claude and OpenAI each produce a structured eligibility + explanation grounded in the retrieved passages.
6. **Confidence.** Compare the two outputs against each other and against the rules engine → confidence per scheme.
7. **Route.** High confidence → deliver. Low confidence → reviewer queue.
8. **Deliver.** A plain-language **action checklist** per eligible scheme: what you get · documents needed · next step · confidence badge · "verify locally" note.
9. **Log.** Anonymized step log + decision + confidence for evaluation.

---

## 7. Data model

**`farmer_profile.csv`** (input schema)

| field | type | notes |
|---|---|---|
| farmer_id | str | synthetic / hashed |
| name | str | optional, not used in logic |
| phone | str | raw stored **with consent**; salted **hash** used in logs + as identity key |
| consent_given | bool | farmer consented to storing their number |
| state / district | str | Punjab + district |
| land_holding_ha | float | drives small/marginal classification |
| land_ownership | enum | owner / tenant / sharecropper |
| category | enum | general / SC / ST / OBC |
| gender | enum | for gender-targeted schemes |
| primary_crop | str | paddy, etc. |
| irrigation | enum | rainfed / irrigated |
| has_kcc | bool | Kisan Credit Card already? |
| bank_account / aadhaar_linked | bool | document readiness |

**`scheme_rules.csv`** (knowledge base — structured side)

| field | notes |
|---|---|
| scheme_id, scheme_name, level (national/state) | |
| eligibility_rules | machine-checkable conditions (for the rules engine) |
| benefit_summary | what the farmer gets |
| documents_required | checklist source |
| application_process / where_to_apply | the "next step" |
| source_url, last_verified | provenance & honesty |
| is_synthetic | clearly flags fabricated fill |

Plus a **document KB** (scheme notes / advisory text) feeding the vector store for RAG.

**Scheme set (verified 2026-06-29):** national (4) — PM-KISAN, Kisan Credit Card, Soil Health Card, PM-KUSUM; Punjab (4) — Free Agricultural Power (PSPCL), Crop Residue Management (CRM) machinery subsidy, Crop Diversification Programme (paddy→maize, ₹17,500/ha), SDRF/NDRF crop-loss relief. *Note: PMFBY (crop insurance) is intentionally excluded — Punjab has never joined PMFBY (still opted out as of 2026), so SDRF/NDRF relief is the de-facto substitute. This real-world nuance is captured in the KB and limitations.*

---

## 8. Confidence model (how the score works)

A per-scheme confidence built from three signals:

- **Rules verdict** (hard pass/fail) — the anchor.
- **Model–model agreement** — do Claude and OpenAI reach the same eligibility verdict + similar reasoning?
- **Model–rules agreement** — do the LLMs agree with the deterministic engine?

Simple, explainable scoring (e.g., weighted agreement → High / Medium / Low). Thresholds tuned on the eval set. **Low** confidence (models disagree, or models contradict rules) → reviewer queue. Displayed to the user as a plain badge with a one-line reason.

> Design principle: the LLMs never override the rules engine on hard criteria — disagreement *lowers confidence and triggers review*, it doesn't silently change the answer.

### Delivery & human-in-the-loop (non-blocking)

The farmer **never waits** on a human. Review is asynchronous oversight, not a gate:

- **Farmer screen:** form → action checklist first (eligible scheme cards: what you get · documents · next step · confidence badge; plus not-eligible reasons + disclaimer) → **then** a follow-up chatbox appears below, seeded with "ask me about these schemes."
- **High-confidence** items are shown immediately, clean.
- **Low-confidence** items are shown immediately too, badged "⚠ Provisional — flagged for expert review, please verify locally," AND dropped into the reviewer dashboard queue.
- **Reviewer dashboard** = oversight/correction queue (not a waiting room). When the reviewer approves/corrects a flagged case, the reviewed answer is **pushed to the farmer's WhatsApp** (uses the stored phone; depends on Twilio send, Day 8).
- **Chat memory:** session-only (Streamlit session state) for now; persisting chat across return visits is deferred (see FUTURE_FEATURES).

---

## 9. Guardrails & responsible use

- Rules engine is the source of truth for hard eligibility; LLMs explain, they don't decide hard facts.
- Every claim is grounded in retrieved KB text; no free-floating scheme invention.
- **Out-of-scope handling:** questions not strictly about the schemes/policies (or with no relevant retrieved passage) get a polite "no relevant information found — please ask about farmer schemes, or verify with your local office" message, never a guessed answer. Enforced via the system prompt (role) + a retrieval-relevance threshold.
- **Roles:** every LLM call uses a **system** message (scope + grounding rules) and a **user** message (profile + rules verdict + retrieved passages); the follow-up chat keeps a **user/assistant** history. The system role is where "stay on-topic, stay grounded" is enforced.
- Low-confidence → human review before delivery.
- Every answer carries a "this is guidance, verify with your local agriculture office / CSC" disclaimer.
- Punjabi and English are both treated as reliable, farmer-friendly output languages.
- No legal/financial guarantees; no collection of sensitive data beyond what's needed; phone stored raw with consent + salted hash, logs use hash only.
- Fallbacks: unknown input → ask; retrieval empty → say so honestly; LLM/API failure → graceful message + log.

---

## 10. Evaluation plan (both methods)

**Quantitative.** A labeled set of ~30–50 synthetic farmer profiles, each annotated with the schemes they *should* match. Measure **precision / recall / F1** of the eligibility output vs. ground truth. Track **model-agreement rate** and **% routed to human**. Report a small table + confusion notes.

**Qualitative.** 5–6 narrated end-to-end scenario walkthroughs (typical paddy smallholder, tenant farmer, SC/ST-targeted scheme, an intentionally ambiguous case that triggers human review, a "no schemes match" case). These double as demo-video material.

**Hallucination / grounding tests.** A dedicated check that every LLM claim is supported by the retrieved passages, not invented:
- Automated grounding check (`guardrails.ground_check`) run over eval cases → report a **grounding rate** (% of answers fully supported by retrieved text).
- Adversarial out-of-scope prompts (e.g. "what's the weather", "tell me a loan shark") must return the polite no-info message, not an answer.
- Fabrication probes: ask about a non-existent/other-state scheme → agent must decline rather than invent details.
- Because eligibility is anchored by the deterministic rules engine, any LLM eligibility claim that contradicts the rules is caught by the confidence layer and flagged.

---

## 11. Tech stack

- **Language:** Python 3.11
- **LLMs:** Anthropic Claude + OpenAI + Google Gemini (via official SDKs), keys in `.env`
- **RAG:** sentence-transformers / provider embeddings + **FAISS or Chroma** vector store
- **Rules engine:** plain Python (transparent, unit-tested)
- **Web UI:** Streamlit (farmer form + reviewer dashboard pages)
- **WhatsApp:** Twilio WhatsApp API, FastAPI/Flask webhook, deployed on **Render/Railway**
- **Storage:** SQLite (profiles, logs, review queue) + CSV for KB
- **Eval/CLI:** a `run_eval.py` over the labeled set
- **Quality:** logging, `requirements.txt`, type hints, unit tests for rules engine

---

## 12. Repository structure (planned)

```
farmer_subsidy_and_advisory_navigation_agent/
├── data/
│   ├── farmer_profile.csv          # sample + eval profiles
│   ├── scheme_rules.csv            # structured KB (real + synthetic, flagged)
│   ├── scheme_docs/                # advisory text for RAG
│   └── eval_labeled.csv            # ground-truth for metrics
├── src/
│   ├── agent_controller.py
│   ├── rules_engine.py
│   ├── retriever.py                # RAG
│   ├── reasoner.py                 # two-LLM calls + parsing
│   ├── confidence.py
│   ├── i18n.py                     # hi / en / cg
│   ├── guardrails.py
│   ├── store.py                    # SQLite, hashing, logging
│   └── utils.py
├── app/
│   ├── streamlit_app.py            # farmer-facing
│   ├── reviewer_dashboard.py       # human-in-loop queue
│   └── whatsapp_webhook.py         # Twilio + FastAPI
├── eval/
│   ├── run_eval.py
│   └── scenarios.md
├── notebooks/
│   └── data_prep_and_exploration.ipynb
├── docs/
│   ├── project_report.md
│   ├── presentation.pdf
│   └── architecture.png
├── tests/
│   └── test_rules_engine.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## 13. 10-day execution plan (solo)

| Day | Focus | Output |
|---|---|---|
| 1 | Finalize spec, set up repo, env, API keys | Skeleton repo, this doc locked |
| 2 | Data: gather/verify real schemes, build `scheme_rules.csv` + docs + synthetic fill | KB ready, sources noted |
| 3 | Rules engine + `FarmerProfile` intake + unit tests | Deterministic eligibility working |
| 4 | RAG retriever over scheme docs | Grounded retrieval working |
| 5 | Three-LLM reasoner + structured output parsing | Claude+OpenAI+Gemini producing checklists |
| 6 | Confidence engine + human-routing logic | Confidence scores + queue |
| 7 | Streamlit farmer app + reviewer dashboard | Working web demo end-to-end |
| 8 | WhatsApp (Twilio) + deploy webhook; i18n (hi/en/cg) | WhatsApp bot live; trilingual output |
| 9 | Eval suite (metrics) + scenarios; guardrails polish | Numbers + narrated runs |
| 10 | README, report, slides, demo video, final cleanup | Submission package |

> Critical path = Days 2–7. WhatsApp is the first thing to descope if a day slips; web app + eval must land.

---

## 14. Deliverables checklist (maps to brief)

- [ ] GitHub repo (clean structure)
- [ ] Dataset/reference files + source links
- [ ] Code (src/app/eval) + requirements.txt
- [ ] README (12-point structure from brief)
- [ ] Project report (docs/)
- [ ] Presentation (8–10 slides)
- [ ] Demo video (5–8 min)
- [ ] Screenshots of prototype
- [ ] Limitations & responsible-use notes
- [ ] Logs of agent steps / sample scenarios
- [ ] Guardrail + fallback logic

---

## 15. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Real scheme data sparse/outdated | Curate what's verifiable, label synthetic fill clearly, cite sources + last-verified date |
| WhatsApp/Twilio + hosting eats time | Channel-agnostic core; web app is the guaranteed demo; WhatsApp is additive |
| Punjab has no PMFBY | Correctly excluded from KB; SDRF/NDRF relief included instead + noted in limitations |
| Two-LLM cost/latency | Cache, limit candidate set before LLM calls, run models in parallel |
| Over-promising in a sensitive domain | Rules-anchored answers, confidence + human review, persistent "verify locally" disclaimer |
| Solo bandwidth | Strict critical path; stretch goals clearly marked |

---

## 16. Open questions for you

1. Do you already have **Claude and OpenAI API keys**, or should the plan include a free-tier fallback (e.g., Groq/Gemini) so cost is zero?
2. Any **specific Punjab district** you want as the demo persona's home (personas currently span Ludhiana, Amritsar, Bathinda, Sangrur, Patiala, Gurdaspur, Hoshiarpur, Firozpur)?
3. For the reviewer dashboard — is a **single shared admin view** fine for the demo, or do you want basic login/roles?
4. Demo video — **screen-recording walkthrough** only, or do you also want a short scripted "farmer story" intro?

---

*Once you approve (or edit) this, Day 1 is: scaffold the repo and lock the scheme list. Nothing is built until you say go.*

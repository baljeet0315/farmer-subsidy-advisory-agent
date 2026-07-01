# Farmer Subsidy & Advisory Navigation Agent

> An AI agent that helps Punjab farmers discover the government schemes and advisories they actually qualify for — delivered as a plain-language action checklist over web and WhatsApp, with three-LLM cross-verification, a confidence score, and human review for sensitive cases.

**Status:** 🚧 In development · Solo project · See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) for the full vision.

---

## 1. Problem statement

Farmers often don't know which government subsidies or advisory services apply to them. Eligibility rules are buried in circulars and bureaucratic language. This agent takes a farmer's profile, matches it against a curated scheme knowledge base, and returns a clear, actionable checklist — keeping humans in control for low-confidence decisions.

## 2. Dataset / reference source

- **Primary:** Data.gov.in agriculture datasets + official national & Punjab scheme notes — https://www.data.gov.in/keywords/agriculture
- **Form:** Curated real scheme data in `data/scheme_rules.csv` + advisory text in `data/scheme_docs/`, supplemented with clearly-labeled synthetic records (`is_synthetic` flag) where official data is sparse. Sources and `last_verified` dates are recorded per scheme.

## 3. Tools used

Python · Anthropic Claude + OpenAI + Google Gemini (three-model ensemble) · ChromaDB + sentence-transformers (RAG) · Streamlit (web + reviewer dashboard) · FastAPI + Twilio (WhatsApp) · SQLite · pytest / scikit-learn (eval).

## 4. Project workflow

Intake → completeness check → deterministic rules pass → RAG retrieval → dual-LLM reasoning → confidence scoring → route (deliver vs. human review) → structured checklist → anonymized logs. See [`PROJECT_SPEC.md`](PROJECT_SPEC.md) §5–6.

## 5. AI / agent component

- **Hybrid eligibility:** deterministic rules engine for hard criteria + RAG-grounded LLM explanation.
- **Three-LLM cross-verification:** Claude, OpenAI, and Gemini reason independently; majority agreement among them and with the rules engine yields a **confidence score**.
- **Confidence-gated human-in-the-loop:** high confidence auto-delivers; low confidence routes to a reviewer queue.

## 6. How to run

```bash
# 1. Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your API keys

# 2. Web app (farmer-facing)
streamlit run app/streamlit_app.py

# 3. Reviewer dashboard
streamlit run app/reviewer_dashboard.py

# 4. WhatsApp webhook (local)
uvicorn app.whatsapp_webhook:app --reload

# 5. Evaluation
python eval/run_eval.py
```

## 7. Demo screenshots

_TODO — added during Day 7–8._

## 8. Results and insights

_TODO — eligibility precision/recall, model-agreement rate, % routed to human (Day 9)._

## 9. Limitations

- Punjab does not implement PMFBY crop insurance; the KB reflects this and uses SDRF/NDRF relief instead.
- Scheme data is a curated snapshot; rules and availability change — always verify with the local agriculture office / CSC.
- Not legal or financial advice. See `docs/` responsible-use notes.

## 10. Future improvements

_TODO — see PROJECT_SPEC §15–16._

## 11. Responsible use

Rules engine anchors hard eligibility; LLMs only explain retrieved content. Low-confidence cases require human review. Phone numbers are hashed; minimal personal data is stored. Every answer carries a "verify locally" disclaimer.

## 12. Team

Solo — B.

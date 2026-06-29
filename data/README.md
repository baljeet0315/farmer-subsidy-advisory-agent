# Data

| File | Purpose |
|---|---|
| `scheme_rules.csv` | Structured scheme KB (eligibility, benefits, documents, process). Built Day 2. |
| `scheme_docs/` | Advisory/scheme text for RAG retrieval. |
| `farmer_profile.csv` | Sample + demo farmer profiles. |
| `eval_labeled.csv` | Farmer profiles annotated with expected eligible schemes (eval ground truth). |

**Provenance:** each scheme row records `source_url` and `last_verified`. Rows that are not from a verifiable official source are flagged `is_synthetic = True`. Real source: https://www.data.gov.in/keywords/agriculture + official national/Chhattisgarh scheme notes.

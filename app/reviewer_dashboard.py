"""Reviewer dashboard — human-in-the-loop queue.

Lists low-confidence cases the agent flagged, so a reviewer can approve or edit
them. On resolution the reviewed answer would be pushed to the farmer's WhatsApp
(wired on Day 8; here it logs the intent).

This is oversight, NOT a blocking gate — farmers already received a provisional
answer. Run:  streamlit run app/reviewer_dashboard.py
"""
from __future__ import annotations

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import store  # noqa: E402


def notify_farmer(case: dict, decision: str, note: str) -> None:
    """Push the reviewed answer to the farmer's WhatsApp. TODO (Day 8): Twilio send.
    For now, record the intent in the audit log."""
    store.log_step(case.get("phone_hash"), "review_notify",
                   {"scheme_id": case["scheme_id"], "decision": decision, "note": note})


def main():
    st.set_page_config(page_title="Reviewer Dashboard", page_icon="🧑‍⚖️", layout="wide")
    st.title("🧑‍⚖️ Reviewer Queue — flagged scheme results")
    st.caption("Low-confidence cases for human oversight. Farmers already have a provisional "
               "answer; your decision refines it and (Day 8) notifies them on WhatsApp.")

    tab_pending, tab_done = st.tabs(["Pending", "Resolved"])

    with tab_pending:
        queue = store.list_review_queue("pending")
        if not queue:
            st.success("Queue is empty — nothing waiting for review. 🎉")
        for case in queue:
            votes = json.loads(case.get("model_votes") or "{}")
            with st.container(border=True):
                st.markdown(f"### {case['scheme_name']}  ·  farmer `{case['farmer_id']}`")
                c1, c2, c3 = st.columns(3)
                c1.metric("Confidence", case["confidence"], f"score {case['confidence_score']}")
                c2.metric("Rules verdict", "Eligible" if case["rules_verdict"] else "Not eligible")
                c3.write(f"**Model votes:** {votes}")
                st.info(case["reason"])
                note = st.text_area("Reviewer note / correction", key=f"note_{case['id']}",
                                    placeholder="Optional: correction or explanation sent to the farmer.")
                b1, b2, _ = st.columns([1, 1, 4])
                if b1.button("✅ Approve", key=f"ap_{case['id']}"):
                    store.resolve_review(case["id"], "approved", note)
                    notify_farmer(case, "approved", note)
                    st.rerun()
                if b2.button("✏️ Edit & resolve", key=f"ed_{case['id']}"):
                    store.resolve_review(case["id"], "edited", note)
                    notify_farmer(case, "edited", note)
                    st.rerun()

    with tab_done:
        for status in ("approved", "edited"):
            done = store.list_review_queue(status)
            for case in done:
                st.write(f"[{status}] **{case['scheme_name']}** · farmer `{case['farmer_id']}` "
                         f"· {case.get('decided_at', '')} · note: {case.get('reviewer_note') or '—'}")


if __name__ == "__main__":
    main()

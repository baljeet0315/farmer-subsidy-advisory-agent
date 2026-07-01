"""Farmer-facing Streamlit app.

Flow: profile form -> full agent pipeline -> action checklist (cards + confidence
badges; low-confidence shown as provisional and queued for review) -> grounded
follow-up chatbox (session-only memory).

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
import uuid

import streamlit as st
from dotenv import load_dotenv

# allow "import src..." when run via `streamlit run app/streamlit_app.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from src import agent_controller as ac  # noqa: E402
from src import store  # noqa: E402
from src.llm_clients import get_default_clients  # noqa: E402
from src.models import Category, FarmerProfile, LandOwnership  # noqa: E402

BADGE = {"high": "🟢 High confidence", "medium": "🟡 Medium confidence", "low": "🔴 Low confidence"}


def build_profile(form: dict) -> FarmerProfile:
    phone = form["phone"].strip() or None
    return FarmerProfile(
        farmer_id=f"web-{uuid.uuid4().hex[:8]}",
        phone=phone,
        phone_hash=store.hash_phone(phone) if phone else None,
        consent_given=form["consent"],
        state="Punjab",
        district=form["district"] or None,
        land_holding_ha=form["land"],
        land_ownership=LandOwnership(form["ownership"]),
        category=Category(form["category"]),
        gender=form["gender"] or None,
        primary_crop=form["crop"] or None,
        irrigation=form["irrigation"],
        has_kcc=form["has_kcc"],
        language=form["language"],
    )


def render_card(assessed, provisional: bool):
    r = assessed.result
    item = assessed.checklist_item
    with st.container(border=True):
        head = f"### {item.scheme_name}"
        st.markdown(head)
        st.caption(BADGE.get(r.confidence.value, r.confidence.value))
        if provisional:
            st.warning("⚠ Provisional — flagged for expert review. Please verify locally; "
                       "we'll follow up if the reviewed answer changes.")
        st.markdown(f"**What you get:** {item.what_you_get}")
        st.markdown("**Documents needed:** " + ", ".join(item.documents_needed))
        st.markdown(f"**Next step:** {item.next_step}")
        st.caption(item.note)


def main():
    st.set_page_config(page_title="Punjab Farmer Scheme Navigator", page_icon="🌾", layout="centered")
    st.title("🌾 Punjab Farmer Subsidy & Advisory Navigator")
    st.caption("Enter your details to see the government schemes you may qualify for. "
               "This is guidance — always verify with your local agriculture office / CSC.")

    clients = get_default_clients()
    if not clients:
        st.error("No LLM API keys found. Add ANTHROPIC/OPENAI/GEMINI keys to .env.")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            district = st.text_input("District", "Ludhiana")
            land = st.number_input("Land you farm (hectares)", min_value=0.0, value=2.0, step=0.5,
                                   help="Enter 0 if you are a landless labourer.")
            ownership = st.selectbox("Land ownership", ["owner", "tenant", "sharecropper"])
            crop = st.text_input("Main crop", "paddy")
        with col2:
            irrigation = st.selectbox("Irrigation", ["irrigated", "rainfed"])
            category = st.selectbox("Category", ["general", "sc", "st", "obc"])
            gender = st.selectbox("Gender", ["", "male", "female", "other"])
            has_kcc = st.checkbox("I already have a Kisan Credit Card")
        language = st.radio("Answer language", ["en", "pa"], format_func=lambda x: {"en": "English", "pa": "ਪੰਜਾਬੀ"}[x], horizontal=True)
        phone = st.text_input("Mobile number (optional)")
        consent = st.checkbox("I consent to storing my number so I can be followed up about my schemes.")
        submitted = st.form_submit_button("Find my schemes")

    if submitted and clients:
        form = dict(district=district, land=land, ownership=ownership, crop=crop,
                    irrigation=irrigation, category=category, gender=gender, has_kcc=has_kcc,
                    language=language, phone=phone, consent=consent)
        profile = build_profile(form)
        with st.spinner("Checking schemes with the rules engine + three AI models…"):
            out = ac.run(profile, clients=clients)
            store.save_profile(profile)
            store.log_step(profile.phone_hash, "assessment",
                           {"delivered": len(out["delivered"]), "flagged": len(out["flagged"])})
            for a in out["flagged"]:
                store.enqueue_review(profile.farmer_id, profile.phone_hash, a)
        # keep context for the chatbox
        st.session_state["profile"] = profile
        st.session_state["eligible_ids"] = [a.scheme.scheme_id for a in out["all"]]
        st.session_state["results"] = out
        st.session_state["chat"] = []

    out = st.session_state.get("results")
    if out:
        st.divider()
        st.subheader(f"You may qualify for {len(out['all'])} scheme(s)")
        for a in out["delivered"]:
            render_card(a, provisional=False)
        for a in out["flagged"]:
            render_card(a, provisional=True)
        if not out["all"]:
            st.info("No schemes matched your profile. Please check with your local agriculture "
                    "office / CSC — you may still be eligible for support not covered here.")

        # --- follow-up chatbox (session memory only) ---
        st.divider()
        st.subheader("Ask a follow-up")
        st.caption("Ask about documents, how to apply, or why you qualify. I answer only from the scheme information.")
        for role, msg in st.session_state.get("chat", []):
            with st.chat_message(role):
                st.markdown(msg)
        if q := st.chat_input("Your question about these schemes…"):
            st.session_state["chat"].append(("user", q))
            with st.chat_message("user"):
                st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("…"):
                    ans = ac.answer_followup(st.session_state["profile"], q,
                                             st.session_state["eligible_ids"], clients=clients)
                st.markdown(ans)
            st.session_state["chat"].append(("assistant", ans))


if __name__ == "__main__":
    main()

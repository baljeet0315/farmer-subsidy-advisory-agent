"""Farmer-facing Streamlit app.

Collects a FarmerProfile via form, runs the agent, and renders the action
checklist with confidence badges and disclaimers.

TODO (Day 7): build form -> agent_controller.run() -> render checklist.
"""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Farmer Scheme Navigator", page_icon="🌾")
    st.title("🌾 Farmer Subsidy & Advisory Navigator")
    st.info("Scaffold — UI to be built on Day 7.")


if __name__ == "__main__":
    main()

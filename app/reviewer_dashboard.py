"""Reviewer dashboard — human-in-the-loop queue.

Lists low-confidence cases routed for review; reviewer approves/edits before
the checklist is delivered to the farmer.

TODO (Day 7): list review queue from store -> approve/edit -> deliver.
"""

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="Reviewer Dashboard", page_icon="🧑‍⚖️")
    st.title("🧑‍⚖️ Reviewer Queue")
    st.info("Scaffold — review queue to be built on Day 7.")


if __name__ == "__main__":
    main()

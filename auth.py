"""Simple password gate for the Streamlit app."""

import streamlit as st


def check_password():
    """Returns True if the user has entered the correct password."""
    if st.session_state.get("authenticated"):
        return True

    st.title("ON24 GEO Benchmark")
    st.markdown("---")
    password = st.text_input("Enter password to access the dashboard:", type="password")

    if password:
        correct = None
        try:
            correct = st.secrets["APP_PASSWORD"]
        except Exception:
            import os
            correct = os.getenv("APP_PASSWORD", "on24on24on24")

        if password == correct:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")

    return False

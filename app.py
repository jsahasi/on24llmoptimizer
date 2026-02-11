import streamlit as st

st.set_page_config(
    page_title="ON24 GEO Benchmark",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("ON24 GEO Benchmarking Dashboard")
st.markdown(
    "Track ON24's footprint in LLM search results vs **Goldcast** and **Zoom**. "
    "Use the sidebar to navigate between views."
)

ENGINE_LABELS = {
    "grok_web_search": "Grok (Web Search)",
    "chatgpt_web_search": "ChatGPT (Web Search)",
    "claude_parametric": "Claude (Parametric)",
}
st.sidebar.selectbox(
    "LLM Engine",
    list(ENGINE_LABELS.keys()),
    key="selected_engine",
    format_func=lambda x: ENGINE_LABELS.get(x, x),
)

# Quick stats from latest run
from db.database import DatabaseManager

db = DatabaseManager()
latest = db.get_latest_run_id()

if latest:
    sov_data = db.get_latest_sov(st.session_state.get("selected_engine", "grok_web_search"))
    if sov_data:
        cols = st.columns(len(sov_data))
        for i, row in enumerate(sov_data):
            with cols[i]:
                name = row["brand"].upper()
                if row["brand"] == "on24":
                    name = "ON24"
                elif row["brand"] == "goldcast":
                    name = "Goldcast"
                elif row["brand"] == "zoom":
                    name = "Zoom"
                st.metric(f"{name} - Share of Voice", f"{row['sov']:.1f}%")
                st.metric("Avg Position", f"#{row['avg_position']:.1f}" if row["avg_position"] else "N/A")
                st.metric("Win Rate", f"{row['win_rate']:.1f}%")
    st.info(f"Latest benchmark run: #{latest}")
else:
    st.warning("No benchmark data yet. Go to **Run Benchmark** to start your first run.")

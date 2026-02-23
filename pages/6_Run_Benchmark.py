import streamlit as st
from db.database import DatabaseManager
from benchmark.engine import BenchmarkEngine

st.set_page_config(page_title="Run Benchmark", layout="wide")
st.header("Run Benchmark")

db = DatabaseManager()

# Show past runs
st.subheader("Benchmark History")
runs = db.get_all_runs()
if runs:
    for run in runs[:10]:
        status_icon = {"completed": "✅", "running": "⏳", "failed": "❌"}.get(run["status"], "❓")
        st.markdown(
            f"{status_icon} **Run #{run['id']}** | {run['run_date']} | "
            f"{run['status'].title()} | {run['completed_queries']}/{run['total_queries']} queries | "
            f"Trigger: {run['trigger_type']}"
        )
else:
    st.info("No benchmark runs yet.")

st.divider()

# Manual trigger
st.subheader("Start New Benchmark")
st.markdown(
    "This will query **32 search terms** across **Grok (web search)** and **Claude (parametric)**. "
    "Each query is parsed by Claude for brand mentions, sentiment, and positioning. "
    "Estimated time: ~10-15 minutes. Estimated cost: ~$2-5."
)

if st.button("Start Benchmark Run", type="primary"):
    try:
        engine = BenchmarkEngine(trigger_type="manual")
    except (ValueError, Exception) as e:
        st.error(f"Cannot start benchmark — missing API keys: {e}")
        st.info("Go to **Manage app** > **Settings** > **Secrets** and add your API keys in TOML format.")
        st.stop()
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, message):
        pct = current / total if total > 0 else 0
        progress_bar.progress(pct)
        status_text.text(message)

    with st.spinner("Running benchmark..."):
        try:
            run_id = engine.run(progress_callback=update_progress)
            progress_bar.progress(1.0)
            status_text.text("Complete!")
            st.success(f"Benchmark completed! Run ID: #{run_id}")
            st.balloons()
        except Exception as e:
            st.error(f"Benchmark failed: {e}")

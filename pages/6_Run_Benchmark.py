import streamlit as st

st.set_page_config(page_title="Run Benchmark", layout="wide")

from auth import check_password
if not check_password():
    st.stop()
from db.database import DatabaseManager
from benchmark.engine import BenchmarkEngine

st.header("Run Benchmark")

db = DatabaseManager()

# Show past runs
st.subheader("Benchmark History")
runs = db.get_all_runs()
stuck_runs = []
if runs:
    for run in runs[:10]:
        status_icon = {"completed": "\u2705", "running": "\u23f3", "failed": "\u274c"}.get(run["status"], "\u2753")
        st.markdown(
            f"{status_icon} **Run #{run['id']}** | {run['run_date']} | "
            f"{run['status'].title()} | {run['completed_queries']}/{run['total_queries']} queries | "
            f"Trigger: {run['trigger_type']}"
        )
        if run["status"] == "running":
            stuck_runs.append(run)
else:
    st.info("No benchmark runs yet.")

# Reset stuck runs / Resume
if stuck_runs:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Resume Interrupted Run")
        latest_stuck = stuck_runs[0]
        remaining = latest_stuck["total_queries"] - latest_stuck["completed_queries"]
        st.markdown(
            f"Run **#{latest_stuck['id']}** was interrupted at "
            f"**{latest_stuck['completed_queries']}/{latest_stuck['total_queries']}** queries. "
            f"Resume to complete the remaining **{remaining}** queries."
        )
        if st.button(f"Resume Run #{latest_stuck['id']}", type="primary"):
            try:
                engine = BenchmarkEngine(trigger_type="manual")
            except (ValueError, Exception) as e:
                st.error(f"Cannot start — missing API keys: {e}")
                st.stop()
            progress_bar = st.progress(latest_stuck["completed_queries"] / latest_stuck["total_queries"])
            status_text = st.empty()

            def update_progress(current, total, message):
                pct = current / total if total > 0 else 0
                progress_bar.progress(min(pct, 1.0))
                status_text.text(message)

            with st.spinner(f"Resuming run #{latest_stuck['id']}..."):
                try:
                    run_id = engine.run(progress_callback=update_progress, run_id=latest_stuck["id"])
                    progress_bar.progress(1.0)
                    status_text.text("Complete!")
                    st.success(f"Benchmark completed! Run ID: #{run_id}")
                    st.balloons()
                except Exception as e:
                    st.warning(f"Run interrupted again: {e}. Click Resume to continue.")

    with col2:
        st.subheader("Reset Stuck Runs")
        st.markdown(f"**{len(stuck_runs)}** run(s) stuck in 'running' state.")
        if st.button("Mark all stuck runs as failed"):
            for run in stuck_runs:
                db.fail_run(run["id"], "Manually reset by user")
            st.success(f"Reset {len(stuck_runs)} stuck run(s).")
            st.rerun()

st.divider()

# Manual trigger
st.subheader("Start New Benchmark")
st.markdown(
    "Sends **32 search queries** to **3 LLM engines** (Grok, ChatGPT, Claude). "
    "Each response is parsed for brand mentions, sentiment, and positioning. "
    "Estimated time: ~20-30 minutes. Estimated cost: ~$3-7. "
    "If interrupted, click **Resume** to continue from where it stopped."
)

if st.button("Start Benchmark Run"):
    try:
        engine = BenchmarkEngine(trigger_type="manual")
    except (ValueError, Exception) as e:
        st.error(f"Cannot start — missing API keys: {e}")
        st.info("Go to **Manage app** > **Settings** > **Secrets** and add your API keys in TOML format.")
        st.stop()
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(current, total, message):
        pct = current / total if total > 0 else 0
        progress_bar.progress(min(pct, 1.0))
        status_text.text(message)

    with st.spinner("Running benchmark..."):
        try:
            run_id = engine.run(progress_callback=update_progress)
            progress_bar.progress(1.0)
            status_text.text("Complete!")
            st.success(f"Benchmark completed! Run ID: #{run_id}")
            st.balloons()
        except Exception as e:
            st.warning(f"Run interrupted: {e}. Click **Resume** to continue from where it stopped.")

import os
import streamlit as st
from db.database import DatabaseManager
from reports.pdf_report import GEOReportGenerator

st.set_page_config(page_title="Reports", layout="wide")
st.header("Generate PDF Report")

db = DatabaseManager()
latest = db.get_latest_run_id()

if not latest:
    st.warning("No completed benchmark data yet. Run a benchmark first.")
    st.stop()

# Show available runs
runs = db.get_all_runs()
completed_runs = [r for r in runs if r["status"] == "completed"]

if not completed_runs:
    st.warning("No completed benchmark runs found.")
    st.stop()

run_options = {r["id"]: f"Run #{r['id']} — {r['run_date']} ({r['total_queries']} queries)" for r in completed_runs}
selected_run = st.selectbox("Select Benchmark Run", list(run_options.keys()),
                            format_func=lambda x: run_options[x])

st.markdown("---")

if st.button("Generate PDF Report", type="primary"):
    with st.spinner("Generating report with charts, tables, and AI recommendations... This may take 30-60 seconds."):
        try:
            gen = GEOReportGenerator(db)
            output_path = gen.generate(run_id=selected_run)

            st.success(f"Report generated successfully!")

            with open(output_path, "rb") as f:
                pdf_bytes = f.read()

            filename = os.path.basename(output_path)
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                type="primary",
            )

            st.info(f"File saved to: `{output_path}`")

        except Exception as e:
            st.error(f"Error generating report: {e}")
            import traceback
            st.code(traceback.format_exc())

# Show existing reports
reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports", "output")
if os.path.exists(reports_dir):
    existing = sorted(
        [f for f in os.listdir(reports_dir) if f.endswith(".pdf")],
        reverse=True,
    )
    if existing:
        st.markdown("---")
        st.subheader("Previous Reports")
        for fname in existing:
            fpath = os.path.join(reports_dir, fname)
            size_kb = os.path.getsize(fpath) / 1024
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"{fname}  ({size_kb:.0f} KB)")
            with col2:
                with open(fpath, "rb") as f:
                    st.download_button(
                        label="Download",
                        data=f.read(),
                        file_name=fname,
                        mime="application/pdf",
                        key=fname,
                    )

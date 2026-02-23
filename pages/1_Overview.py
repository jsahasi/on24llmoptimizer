import streamlit as st
from auth import check_password
if not check_password():
    st.stop()
import pandas as pd
import plotly.express as px
from db.database import DatabaseManager

st.set_page_config(page_title="Overview", layout="wide")
st.header("GEO Benchmark Overview")

db = DatabaseManager()
engine = st.session_state.get("selected_engine", "grok_web_search")
latest = db.get_latest_run_id()

if not latest:
    st.warning("No benchmark data yet. Run a benchmark first.")
    st.stop()

# KPI Cards
sov_data = db.get_latest_sov(engine)
if sov_data:
    cols = st.columns(3)
    brand_colors = {"on24": "#1E88E5", "goldcast": "#FFC107", "zoom": "#43A047"}

    for i, row in enumerate(sov_data):
        name = {"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"}.get(row["brand"], row["brand"])
        with cols[i]:
            st.subheader(name)
            c1, c2 = st.columns(2)
            c1.metric("Share of Voice", f"{row['sov']:.1f}%")
            c2.metric("Win Rate", f"{row['win_rate']:.1f}%")
            c3, c4 = st.columns(2)
            c3.metric("Avg Position", f"#{row['avg_position']:.1f}" if row["avg_position"] else "N/A")
            c4.metric("Avg Sentiment", f"{row['avg_sentiment']:.2f}" if row["avg_sentiment"] is not None else "N/A")

    # SOV bar chart
    df = pd.DataFrame(sov_data)
    df["brand"] = df["brand"].map({"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"})
    fig = px.bar(df, x="brand", y="sov", color="brand",
                 title="Share of Voice by Brand",
                 labels={"sov": "Share of Voice (%)", "brand": ""},
                 color_discrete_map={"ON24": "#1E88E5", "Goldcast": "#FFC107", "Zoom": "#43A047"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# Category breakdown
st.subheader("Performance by Query Category")
breakdown = db.get_search_term_breakdown(latest, engine)
if breakdown:
    df = pd.DataFrame(breakdown)
    cat_summary = (
        df.groupby(["query_category", "brand"])
        .agg({"is_mentioned": "mean", "is_winner": "mean", "avg_sentiment_score": "mean"})
        .reset_index()
    )
    cat_summary["is_mentioned"] = (cat_summary["is_mentioned"] * 100).round(1)
    cat_summary["is_winner"] = (cat_summary["is_winner"] * 100).round(1)
    cat_summary.columns = ["Category", "Brand", "Mention Rate %", "Win Rate %", "Avg Sentiment"]
    cat_summary["Brand"] = cat_summary["Brand"].map({"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"})
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)

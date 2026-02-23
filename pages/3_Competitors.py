import streamlit as st
from auth import check_password
if not check_password():
    st.stop()
import pandas as pd
import plotly.graph_objects as go
from db.database import DatabaseManager

st.set_page_config(page_title="Competitors", layout="wide")
st.header("Competitor Comparison")

db = DatabaseManager()
engine = st.session_state.get("selected_engine", "grok_web_search")
latest = db.get_latest_run_id()

if not latest:
    st.warning("No benchmark data yet.")
    st.stop()

sov_data = db.get_latest_sov(engine)
if not sov_data:
    st.warning("No data available.")
    st.stop()

brand_map = {"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"}
colors = {"ON24": "#1E88E5", "Goldcast": "#FFC107", "Zoom": "#43A047"}

# Side by side
cols = st.columns(3)
for i, row in enumerate(sov_data):
    name = brand_map.get(row["brand"], row["brand"])
    with cols[i]:
        st.subheader(name)
        st.metric("Share of Voice", f"{row['sov']:.1f}%")
        st.metric("Win Rate", f"{row['win_rate']:.1f}%")
        st.metric("Avg Position", f"#{row['avg_position']:.1f}" if row["avg_position"] else "N/A")
        st.metric("Avg Sentiment", f"{row['avg_sentiment']:.2f}" if row["avg_sentiment"] is not None else "N/A")

# Radar chart
st.subheader("Competitive Radar")
metrics_labels = ["Share of Voice", "Win Rate", "Sentiment (scaled)", "Position Score"]

fig = go.Figure()
for row in sov_data:
    name = brand_map.get(row["brand"], row["brand"])
    pos_score = max(0, 100 - (row["avg_position"] or 5) * 15)
    sent_scaled = ((row["avg_sentiment"] or 0) + 1) * 50

    fig.add_trace(go.Scatterpolar(
        r=[row["sov"], row["win_rate"], sent_scaled, pos_score],
        theta=metrics_labels,
        fill="toself",
        name=name,
        line_color=colors.get(name, "#999"),
    ))

fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])))
st.plotly_chart(fig, use_container_width=True)

# Head-to-head per category
st.subheader("Category-Level Comparison")
breakdown = db.get_search_term_breakdown(latest, engine)
if breakdown:
    df = pd.DataFrame(breakdown)
    for cat in sorted(df["category"].unique()):
        cat_df = df[df["category"] == cat]
        st.markdown(f"**{cat.replace('_', ' ').title()}**")

        summary = (
            cat_df.groupby("brand")
            .agg({"is_mentioned": "mean", "is_winner": "mean"})
            .reset_index()
        )
        summary["is_mentioned"] = (summary["is_mentioned"] * 100).round(1)
        summary["is_winner"] = (summary["is_winner"] * 100).round(1)
        summary["brand"] = summary["brand"].map(brand_map)
        summary.columns = ["Brand", "Mention Rate %", "Win Rate %"]
        st.dataframe(summary, use_container_width=True, hide_index=True)

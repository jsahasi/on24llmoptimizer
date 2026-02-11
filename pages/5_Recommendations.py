import streamlit as st
from db.database import DatabaseManager
from analysis.recommendations import RecommendationEngine

st.set_page_config(page_title="Recommendations", layout="wide")
st.header("AI-Powered GEO Recommendations")

db = DatabaseManager()
latest = db.get_latest_run_id()

if not latest:
    st.warning("No benchmark data yet. Run a benchmark first.")
    st.stop()

if st.button("Generate Recommendations", type="primary"):
    with st.spinner("Claude is analyzing your benchmark data..."):
        engine = RecommendationEngine(db)
        recs = engine.generate_recommendations(latest)
        st.session_state["recommendations"] = recs

recs = st.session_state.get("recommendations")
if not recs:
    st.info("Click 'Generate Recommendations' to get AI-powered tactical advice.")
    st.stop()

# Executive Summary
st.subheader("Executive Summary")
st.info(recs.get("executive_summary", ""))

if recs.get("on24_sov_assessment"):
    st.markdown(f"**SOV Assessment:** {recs['on24_sov_assessment']}")

# Wins and Losses
col1, col2 = st.columns(2)

with col1:
    st.subheader("ON24 Wins")
    for win in recs.get("wins", []):
        st.success(f"**{win['query']}**\n\n{win['reason']}")

with col2:
    st.subheader("ON24 Losses")
    for loss in recs.get("losses", []):
        st.error(f"**{loss['query']}**\n\nWinner: {loss['winning_competitor']}\n\n{loss['reason']}")

# Prioritized Recommendations
st.subheader("Tactical Recommendations")
for rec in sorted(recs.get("recommendations", []), key=lambda x: x.get("priority", 99)):
    impact = rec.get("expected_impact", "medium")
    icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(impact, "⚪")
    with st.expander(f"{icon} P{rec.get('priority', '?')}: {rec.get('action', '')[:80]}"):
        st.markdown(f"**Category:** {rec.get('category', '').replace('_', ' ').title()}")
        st.markdown(f"**Impact:** {impact.title()}")
        st.markdown(f"**Rationale:** {rec.get('rationale', '')}")

# Competitor Insights
st.subheader("Competitor Insights")
insights = recs.get("competitor_insights", {})

tab1, tab2 = st.tabs(["Goldcast", "Zoom"])
with tab1:
    gc = insights.get("goldcast", {})
    st.markdown(f"**Threat Level:** {gc.get('threat_level', 'N/A').title()}")
    st.markdown(f"**Strengths:** {gc.get('strengths', 'N/A')}")
    st.markdown(f"**Weaknesses:** {gc.get('weaknesses', 'N/A')}")

with tab2:
    zm = insights.get("zoom", {})
    st.markdown(f"**Threat Level:** {zm.get('threat_level', 'N/A').title()}")
    st.markdown(f"**Strengths:** {zm.get('strengths', 'N/A')}")
    st.markdown(f"**Weaknesses:** {zm.get('weaknesses', 'N/A')}")

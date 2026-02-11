import streamlit as st
import pandas as pd
from db.database import DatabaseManager

st.set_page_config(page_title="Search Terms", layout="wide")
st.header("Search Term Analysis")

db = DatabaseManager()
engine = st.session_state.get("selected_engine", "grok_web_search")
latest = db.get_latest_run_id()

if not latest:
    st.warning("No benchmark data yet.")
    st.stop()

breakdown = db.get_search_term_breakdown(latest, engine)
if not breakdown:
    st.warning("No data for selected engine.")
    st.stop()

df = pd.DataFrame(breakdown)

# Pivot to show one row per query with columns per brand
categories = sorted(df["category"].unique())
selected_cat = st.selectbox("Filter by Category", ["All"] + categories)
if selected_cat != "All":
    df = df[df["category"] == selected_cat]

# Build comparison table
rows = []
for qid in df["query_id"].unique():
    q_data = df[df["query_id"] == qid]
    query_text = q_data.iloc[0]["query_text"]
    category = q_data.iloc[0]["category"]

    row = {"Query": query_text, "Category": category}
    winner = None

    for _, r in q_data.iterrows():
        brand = r["brand"]
        name = {"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"}.get(brand, brand)
        pos_val = r['first_mention_position']
        pos = f"#{int(pos_val)}" if pos_val and not pd.isna(pos_val) else "-"
        row[f"{name} Position"] = pos
        sent_val = r['avg_sentiment_score']
        row[f"{name} Sentiment"] = f"{sent_val:.2f}" if sent_val is not None and not pd.isna(sent_val) else "-"
        if r["is_winner"]:
            winner = name

    row["Winner"] = winner or "None"
    rows.append(row)

result_df = pd.DataFrame(rows)

# Color the winner column
def highlight_winner(val):
    if val == "ON24":
        return "background-color: #BBDEFB"
    elif val == "Goldcast":
        return "background-color: #FFF9C4"
    elif val == "Zoom":
        return "background-color: #C8E6C9"
    return ""

styled = result_df.style.map(highlight_winner, subset=["Winner"])
st.dataframe(styled, use_container_width=True, hide_index=True, height=700)

# Summary stats
st.subheader("Win Summary")
if rows:
    wins = pd.DataFrame(rows)["Winner"].value_counts()
    cols = st.columns(4)
    for i, (brand, count) in enumerate(wins.items()):
        if i < 4:
            cols[i].metric(brand, f"{count} wins")

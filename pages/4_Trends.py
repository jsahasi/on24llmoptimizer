import streamlit as st
import pandas as pd
import plotly.express as px
from db.database import DatabaseManager
from analysis.trends import TrendAnalyzer

st.set_page_config(page_title="Trends", layout="wide")
st.header("GEO Trend Analysis")

db = DatabaseManager()
trends = TrendAnalyzer(db)
engine = st.session_state.get("selected_engine", "grok_web_search")

days = st.slider("Days of history", 7, 90, 30)

brand_map = {"on24": "ON24", "goldcast": "Goldcast", "zoom": "Zoom"}
color_map = {"ON24": "#1E88E5", "Goldcast": "#FFC107", "Zoom": "#43A047"}


def plot_trend(data, y_col, title, y_label, invert_y=False):
    if not data:
        st.info(f"No data for {title}")
        return
    df = pd.DataFrame(data)
    df["brand"] = df["brand"].map(brand_map)
    fig = px.line(df, x="date", y=y_col, color="brand", title=title,
                  labels={y_col: y_label, "date": "Date", "brand": "Brand"},
                  color_discrete_map=color_map, markers=True)
    if invert_y:
        fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True)


# SOV Trend
plot_trend(trends.get_sov_trend(engine, days), "sov", "Share of Voice Over Time", "SOV (%)")

# Position Trend
plot_trend(trends.get_position_trend(engine, days), "avg_position",
           "Average Mention Position Over Time", "Position (lower = better)", invert_y=True)

# Sentiment Trend
plot_trend(trends.get_sentiment_trend(engine, days), "sentiment",
           "Sentiment Score Over Time", "Sentiment (-1 to 1)")

# Win Rate Trend
plot_trend(trends.get_win_rate_trend(engine, days), "win_rate",
           "Win Rate Over Time", "Win Rate (%)")

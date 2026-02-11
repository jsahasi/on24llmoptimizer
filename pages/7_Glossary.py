import streamlit as st

st.set_page_config(page_title="About & Glossary", layout="wide")
st.header("About This Application")

st.markdown("""
## What This App Does

The **ON24 GEO Benchmarking Tool** measures how ON24 appears in AI-powered search results compared to
competitors **Goldcast** and **Zoom** (Webinars/Events only). It answers the questions:

- **Where does ON24 win?** Which search queries position ON24 as the top recommendation?
- **Where do competitors win?** Which queries favor Goldcast or Zoom over ON24?
- **How is visibility trending?** Are we gaining or losing ground in LLM search results over time?
- **What can ON24 do to improve?** AI-generated tactical recommendations to boost LLM visibility.

## How It Works

### 1. Query Execution
The app sends **32 industry-relevant search queries** (e.g., "Best webinar platform for B2B marketing")
to **three LLM engines**:

- **Grok (xAI)** - Uses live web search to return real-time results with citations. This is the primary
  GEO benchmark since it reflects what users actually see when searching with AI.
- **ChatGPT (OpenAI)** - Uses web search to return real-time results with citations. The most widely
  used consumer AI search engine.
- **Claude (Anthropic)** - Answers from training data only (no web search). Measures "parametric knowledge" -
  what the model inherently knows about ON24. This is a leading indicator of future visibility.

### 2. Response Parsing
Each LLM response is analyzed by Claude to extract:
- Which brands are mentioned and in what order
- The sentiment toward each brand (positive/neutral/negative)
- Whether a brand is the primary recommendation
- Which URLs are cited (tracking www.on24.com vs event.on24.com)

### 3. Metrics Computation
Results are aggregated into daily metrics per brand, per query, per engine and stored in a local SQLite database.

### 4. Dashboard Visualization
The Streamlit dashboard presents the data across six views: Overview, Search Terms, Competitors, Trends,
Recommendations, and Run Benchmark.

### 5. Daily Tracking
The benchmark can be run daily (manually or via Windows Task Scheduler) to track changes over time.

---
""")

st.header("Glossary of Terms")

glossary = {
    "GEO (Generative Engine Optimization)":
        "The practice of optimizing a brand's content and online presence to appear favorably in "
        "AI-generated search results (ChatGPT, Grok, Claude, Perplexity, Google AI Overviews). "
        "The AI equivalent of SEO.",

    "Share of Voice (SOV)":
        "The percentage of queries where a brand is mentioned at all in the LLM response. "
        "Example: If ON24 is mentioned in 30 out of 32 queries, its SOV is 93.8%. "
        "Higher is better.",

    "Mention Position":
        "The ordinal position where a brand first appears in an LLM response. Position #1 means "
        "the brand is mentioned first. Lower is better. Average position across all queries where "
        "the brand is mentioned.",

    "Win Rate":
        "The percentage of queries where a brand is determined to be the 'winner' - the most "
        "favorably positioned or recommended brand. Determined by: (1) being the primary recommendation, "
        "(2) being mentioned first, (3) having the highest sentiment score.",

    "Sentiment Score":
        "A measure of how positively or negatively a brand is described in the LLM response. "
        "Ranges from -1.0 (very negative) to +1.0 (very positive). 0.0 is neutral. "
        "Extracted by Claude analyzing the context around each brand mention.",

    "Primary Recommendation":
        "When an LLM explicitly recommends one brand as the top/best choice for the query. "
        "Example: 'For enterprise B2B webinars, ON24 is the top recommendation.'",

    "Citation":
        "A URL referenced by an LLM in its response. Grok and ChatGPT include citations with web search. "
        "We track whether citations point to www.on24.com (target) vs event.on24.com (webinar pages).",

    "Parametric Knowledge":
        "What an LLM knows from its training data, without accessing the web. Claude's responses "
        "represent parametric knowledge. If ON24 is well-represented in Claude's training data, "
        "it indicates strong brand presence in high-quality content sources.",

    "Web Search (Live)":
        "When an LLM searches the internet in real-time to answer a query. Grok and ChatGPT "
        "use web search, making their results reflect current online content. This is the primary "
        "GEO benchmark.",

    "Query Categories":
        "The 32 search queries are organized into 5 categories: "
        "**Platform Comparison** (head-to-head, listicles, alternatives), "
        "**Use Case** (demand gen, virtual conferences, industry verticals), "
        "**Feature** (CRM integration, engagement, AI, automation), "
        "**ROI/Strategy** (webinar ROI, pipeline generation, conversion benchmarks), "
        "**Technical** (API, SSO, branding, accessibility).",

    "Benchmark Run":
        "A single execution of all 32 queries across all LLM engines. Each run produces a snapshot "
        "of the competitive landscape. Running daily enables trend analysis.",

    "www.on24.com vs event.on24.com":
        "ON24 has two main domains. **www.on24.com** is the corporate website (target for driving traffic). "
        "**event.on24.com** hosts individual webinar events. This tool tracks citations to both but focuses "
        "on driving traffic to the corporate site.",

    "Zoom Filtering":
        "Zoom is a broad brand. This tool specifically tracks **Zoom Webinars** and **Zoom Events** "
        "(virtual event products). Mentions of Zoom Meetings or general video conferencing are "
        "flagged and excluded from competitive metrics.",
}

for term, definition in glossary.items():
    with st.expander(f"**{term}**"):
        st.markdown(definition)

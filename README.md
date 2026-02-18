# ON24 GEO Benchmarking Tool

Track and improve ON24's visibility in AI-powered search results (LLMs like ChatGPT, Grok, Claude) compared to competitors Goldcast and Zoom.

## What This Does

1. **Benchmarks ON24's GEO footprint** - Sends 32 industry-relevant search queries to 3 LLM engines and analyzes how ON24 is mentioned vs competitors
2. **Tracks trends daily** - Stores results in SQLite and charts Share of Voice, mention position, sentiment, and win rate over time
3. **Identifies winners and losers** - Shows which search terms ON24 wins on and where competitors have the advantage
4. **Provides tactical recommendations** - AI-generated suggestions to improve ON24's visibility in LLM search results and drive more traffic to www.on24.com

## Key Metrics

| Metric | Description |
|--------|-------------|
| Share of Voice | % of queries where each brand is mentioned |
| Mention Position | Where in the response each brand appears (1st, 2nd, 3rd) |
| Sentiment Score | Positive/Neutral/Negative tone per mention (-1.0 to 1.0) |
| Citation Count | URLs cited per brand, with www.on24.com vs event.on24.com split |
| Win Rate | % of queries where each brand is the top recommendation |

## Competitors Tracked

- **ON24** (www.on24.com) - Target brand
- **Goldcast** (goldcast.io) - B2B event marketing competitor
- **Zoom** (Webinars/Events only) - Excludes Zoom Meetings

## LLM Engines

- **Grok Web Search** (xAI) - Real-time results via xAI Responses API with live web search
- **ChatGPT Web Search** (OpenAI) - Real-time results via OpenAI Responses API with web search preview
- **Claude Parametric** (Anthropic) - Measures what Claude knows from training data (no web search)

## Setup

### Prerequisites
- Python 3.10+
- API keys for Anthropic Claude, xAI Grok, and OpenAI

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your-anthropic-key
XAI_API_KEY=your-xai-key
OPENAI_API_KEY=your-openai-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## Usage

### Launch Dashboard

```bash
streamlit run app.py
```

### Run a Benchmark Manually

```bash
python run_benchmark.py
```

### Generate PDF Report

```bash
python reports/pdf_report.py
```

Or use the **Reports** page in the dashboard to generate and download.

### Email Report

```bash
python -m reports.email_report reports/output/ON24_GEO_Report_2026-02-11.pdf recipient@example.com
```

Requires SMTP settings in `.env`.

### Schedule Weekly Benchmarks (Windows)

Run as Administrator:
```batch
scheduler\install_task.bat
```

This creates a Windows Task Scheduler job that runs the benchmark weekly (Mondays at 6:00 AM).

## Dashboard Pages

1. **Overview** - KPI cards with Share of Voice, avg position, sentiment, win rate
2. **Search Terms** - Per-query analysis showing which brand wins each search term
3. **Competitors** - Side-by-side comparison of ON24 vs Goldcast vs Zoom with radar chart
4. **Trends** - Line charts tracking metrics over time
5. **Recommendations** - AI-generated tactical suggestions to improve GEO performance
6. **Run Benchmark** - Manual trigger with progress bar and run history
7. **Glossary** - Explanation of what the app does and definitions of all terms
8. **Reports** - Generate and download professional PDF reports with charts and tables

## Query Categories (32 queries)

- **Platform Comparison** (8) - "Best webinar platform for B2B", head-to-head comparisons
- **Use Case** (7) - Demand gen, virtual conferences, product demos, industry verticals
- **Feature** (7) - CRM integration, engagement tools, AI analytics, automation
- **ROI/Strategy** (5) - Webinar ROI, pipeline generation, conversion benchmarks
- **Technical** (5) - API integrations, SSO, custom branding, accessibility

## Estimated Cost

~$3-7 per benchmark run across all 3 LLM engines.

## Architecture

```
Queries (32) --> Grok (web search) + ChatGPT (web search) + Claude (parametric)
                              |
                    Claude Parser (structured output)
                              |
                    SQLite (6 tables, WAL mode)
                              |
                    Streamlit Dashboard (8 pages)
                              |
                    Claude Recommendations Engine
                              |
                    PDF Report (reportlab + matplotlib)
                              |
                    Email via SMTP (Gmail)
```

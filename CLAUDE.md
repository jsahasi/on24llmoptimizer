# ON24 GEO Benchmarking Application

## Project Overview
Benchmarks ON24's footprint in LLM search results (GEO) against Goldcast and Zoom (webinars/events only). Tracks daily, charts trends, provides tactical recommendations.

## Tech Stack
- Python 3.12 + Streamlit + SQLite (WAL mode) + Plotly
- APIs: Anthropic Claude `claude-sonnet-4-5-20250929` + xAI Grok `grok-4-0709` (web search) + OpenAI `gpt-4o` (web search)

## API Details
- Grok: `POST https://api.x.ai/v1/responses` with `tools: [{"type": "web_search"}]`, input as string
- Grok web search requires grok-4 family models (grok-3 not supported for tools)
- OpenAI: `client.responses.create()` with `tools: [{"type": "web_search_preview"}]`, falls back to chat completions
- Claude: `anthropic.Anthropic().messages.create()` - standard Messages API (parametric only, no web search)
- Parser uses Claude with simplified JSON prompt

## Project Structure
- `config/` - Settings, brand definitions, 32 query templates across 5 categories
- `db/` - SQLite schema (6 tables) and database manager
- `benchmark/` - Grok client, OpenAI client, Claude client, orchestrator engine
- `analysis/` - Response parser, metrics calculator, trends analyzer, recommendation engine
- `pages/` - Streamlit multi-page dashboard (7 pages)
- `app.py` - Streamlit entry point
- `run_benchmark.py` - Standalone script for Windows Task Scheduler

## Key Design Decisions
- ON24 domain filtering: www.on24.com (target) vs event.on24.com (excluded from target metric)
- Zoom filtering: Only tracks Zoom Webinars/Events context, excludes Zoom Meetings
- Three LLM engines: Grok (web search) + ChatGPT (web search) + Claude (parametric)
- Parser normalizes Claude's varying JSON output formats
- Pre-aggregated daily_metrics table for fast dashboard queries
- Winner determined by: primary recommendation > first mention position > sentiment score

## Commands
- Dashboard: `streamlit run app.py`
- Manual benchmark: `python run_benchmark.py`
- Install deps: `pip install -r requirements.txt`
- Task Scheduler: Run `scheduler\install_task.bat` as Administrator

## Build Status - COMPLETE
- [x] Foundation (config, db, requirements)
- [x] API Clients (Grok + ChatGPT + Claude)
- [x] Response Parser (Claude-powered)
- [x] Benchmark Engine + Metrics
- [x] Streamlit Dashboard (7 pages incl. Glossary)
- [x] Recommendations Engine
- [x] Scheduler

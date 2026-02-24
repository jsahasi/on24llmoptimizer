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
- `config/` - Settings (lazy secret loading via `_get_secret`), brand definitions, 32 query templates
- `db/` - SQLite schema (6 tables) and database manager
- `benchmark/` - Grok client, OpenAI client, Claude client, parallel orchestrator engine (ThreadPoolExecutor)
- `analysis/` - Response parser, metrics calculator, trends analyzer, recommendation engine
- `pages/` - Streamlit multi-page dashboard (8 pages, all password-protected)
- `reports/` - PDF report generator (reportlab + matplotlib) + email sender (SMTP)
- `auth.py` - Password gate for all pages (password in `APP_PASSWORD` secret)
- `app.py` - Streamlit entry point
- `run_benchmark.py` - Standalone script for Windows Task Scheduler
- `.streamlit/config.toml` - Streamlit Cloud config (headless, ON24 theme)

## Key Design Decisions
- ON24 domain filtering: www.on24.com (target) vs event.on24.com (excluded from target metric)
- Zoom filtering: Only tracks Zoom Webinars/Events context, excludes Zoom Meetings
- Three LLM engines: Grok (web search) + ChatGPT (web search) + Claude (parametric)
- Parallel execution: 9 workers (3 queries x 3 engines) with thread-safe per-engine rate limiting
- Resumable runs: interrupted benchmarks can be continued from where they stopped
- Parser normalizes Claude's varying JSON output formats
- Pre-aggregated daily_metrics table for fast dashboard queries
- Winner determined by: primary recommendation > first mention position > sentiment score
- Only retry transient API errors (rate limit, connection, server); auth errors fail immediately

## Commands
- Dashboard: `streamlit run app.py`
- Manual benchmark: `python run_benchmark.py`
- Generate PDF report: `python reports/pdf_report.py`
- Email report: `python -m reports.email_report <pdf_path> <to_email>`
- Install deps: `pip install -r requirements.txt`
- Task Scheduler (weekly): Run `scheduler\install_task.bat` as Administrator

## Deployment
- **Streamlit Cloud**: https://on24llmoptimizer.streamlit.app (public, password-protected)
- **GitHub**: https://github.com/jsahasi/on24llmoptimizer (public repo)
- Secrets configured via Streamlit Cloud Settings > Secrets (TOML format)
- API keys resolved lazily via `_get_secret()` — works with both .env and st.secrets

## Known Issues
- reportlab's default stylesheet includes `BodyText` — must modify it in-place, not re-add
- Streamlit Cloud TOML secrets: API keys must be on a single line (no line breaks in values)
- OPENAI_API_KEY is 164 chars — verify length in API Key Status expander if auth errors occur
- Streamlit Cloud may timeout on long runs — use Resume button to continue interrupted benchmarks

## Build Status - COMPLETE
- [x] Foundation (config, db, requirements)
- [x] API Clients (Grok + ChatGPT + Claude)
- [x] Response Parser (Claude-powered)
- [x] Benchmark Engine + Metrics
- [x] Streamlit Dashboard (8 pages incl. Glossary + Reports)
- [x] PDF Report Generator (reportlab + matplotlib)
- [x] Email Report via SMTP (Gmail)
- [x] Recommendations Engine
- [x] Weekly Scheduler (Mondays 6 AM)
- [x] Password Protection (all pages)
- [x] Streamlit Cloud Deployment
- [x] Parallel Execution (9 workers, ~5-8 min)
- [x] Resumable Runs (interrupted benchmarks continue from last checkpoint)

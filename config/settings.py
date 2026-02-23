import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_secret(key):
    """Read from env vars first, fall back to Streamlit secrets (for Cloud deployment)."""
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return None


# API Keys
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY")
XAI_API_KEY = _get_secret("XAI_API_KEY")
OPENAI_API_KEY = _get_secret("OPENAI_API_KEY")

# xAI Grok Configuration
XAI_BASE_URL = "https://api.x.ai/v1"
XAI_RESPONSES_URL = f"{XAI_BASE_URL}/responses"
GROK_MODEL = "grok-4-0709"

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o"
OPENAI_DELAY_SECONDS = 1.5

# Claude Configuration
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
CLAUDE_MODEL_RECOMMENDATIONS = "claude-sonnet-4-5-20250929"

# Rate Limiting
GROK_RPM = 30
GROK_DELAY_SECONDS = 2.5
CLAUDE_RPM = 50
CLAUDE_DELAY_SECONDS = 1.5

# Database
DB_PATH = str(PROJECT_ROOT / "data" / "geo_benchmark.db")

# Brands
TRACKED_BRANDS = ["on24", "goldcast", "zoom"]
ON24_TARGET_DOMAIN = "www.on24.com"
ON24_EXCLUDE_DOMAIN = "event.on24.com"

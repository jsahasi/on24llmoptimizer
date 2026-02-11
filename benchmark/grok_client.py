import time
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import XAI_API_KEY, XAI_RESPONSES_URL, GROK_DELAY_SECONDS


GROK_MODEL = "grok-4-0709"


class GrokWebSearchClient:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {XAI_API_KEY}",
        }
        self._last_call = 0

    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < GROK_DELAY_SECONDS:
            time.sleep(GROK_DELAY_SECONDS - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((requests.exceptions.RequestException,)),
    )
    def query(self, query_text: str) -> dict:
        self._wait()

        system_msg = (
            "You are a knowledgeable B2B marketing technology analyst. "
            "When answering questions about webinar platforms and virtual event solutions, "
            "provide comprehensive, balanced comparisons. Always cite your sources with URLs. "
            "Focus on enterprise B2B use cases. When discussing Zoom, focus ONLY on "
            "Zoom Webinars and Zoom Events (not Zoom Meetings or video conferencing)."
        )

        payload = {
            "model": GROK_MODEL,
            "input": f"{system_msg}\n\n{query_text}",
            "tools": [{"type": "web_search"}],
        }

        resp = requests.post(XAI_RESPONSES_URL, headers=self.headers, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return self._parse(data)

    def _parse(self, data: dict) -> dict:
        full_text = ""
        citations = []

        for item in data.get("output", []):
            # Items with content array (the actual response text)
            if "content" in item and isinstance(item["content"], list):
                for block in item["content"]:
                    if block.get("type") == "output_text":
                        full_text += block.get("text", "")
                        for ann in block.get("annotations", []):
                            if ann.get("type") == "url_citation":
                                citations.append({
                                    "url": ann.get("url", ""),
                                    "title": ann.get("title", ""),
                                })

        # Deduplicate citations by URL
        seen = set()
        unique_citations = []
        for c in citations:
            if c["url"] not in seen:
                seen.add(c["url"])
                unique_citations.append(c)

        return {
            "raw_response": full_text,
            "citations": unique_citations,
            "model": data.get("model", GROK_MODEL),
            "usage": data.get("usage", {}),
        }

import time
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import OPENAI_API_KEY, OPENAI_MODEL, OPENAI_DELAY_SECONDS


class OpenAISearchClient:
    """Client for OpenAI ChatGPT with web search via the responses API."""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = OPENAI_MODEL
        self._last_call = 0

    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < OPENAI_DELAY_SECONDS:
            time.sleep(OPENAI_DELAY_SECONDS - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((Exception,)),
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

        # Try responses API with web search first, fall back to chat completions
        try:
            return self._query_with_web_search(system_msg, query_text)
        except Exception:
            return self._query_chat_completions(system_msg, query_text)

    def _query_with_web_search(self, system_msg: str, query_text: str) -> dict:
        """Use OpenAI Responses API with web_search tool."""
        response = self.client.responses.create(
            model=self.model,
            input=f"{system_msg}\n\n{query_text}",
            tools=[{"type": "web_search_preview"}],
        )

        full_text = ""
        citations = []

        for item in response.output:
            if hasattr(item, "content") and item.content:
                for block in item.content:
                    if hasattr(block, "text"):
                        full_text += block.text
                    if hasattr(block, "annotations"):
                        for ann in block.annotations:
                            if hasattr(ann, "url") and ann.url:
                                citations.append({
                                    "url": ann.url,
                                    "title": getattr(ann, "title", ""),
                                })

        # Deduplicate citations
        seen = set()
        unique_citations = []
        for c in citations:
            if c["url"] not in seen:
                seen.add(c["url"])
                unique_citations.append(c)

        return {
            "raw_response": full_text,
            "citations": unique_citations,
            "model": self.model,
            "usage": {},
        }

    def _query_chat_completions(self, system_msg: str, query_text: str) -> dict:
        """Fallback to standard chat completions (no web search)."""
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": query_text},
            ],
        )

        return {
            "raw_response": response.choices[0].message.content,
            "citations": [],
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
        }

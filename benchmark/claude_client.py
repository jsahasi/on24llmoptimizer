import time
import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_DELAY_SECONDS


class ClaudeParametricClient:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        self.model = CLAUDE_MODEL
        self._last_call = 0

    def _wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < CLAUDE_DELAY_SECONDS:
            time.sleep(CLAUDE_DELAY_SECONDS - elapsed)
        self._last_call = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.InternalServerError)),
    )
    def query(self, query_text: str) -> dict:
        self._wait()

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=(
                "You are a knowledgeable B2B marketing technology analyst. "
                "When answering questions about webinar platforms and virtual event solutions, "
                "provide comprehensive, balanced comparisons based on your knowledge. "
                "Focus on enterprise B2B use cases. When discussing Zoom, focus ONLY on "
                "Zoom Webinars and Zoom Events (not Zoom Meetings or video conferencing)."
            ),
            messages=[{"role": "user", "content": query_text}],
        )

        return {
            "raw_response": response.content[0].text,
            "model": response.model,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            "citations": [],
        }

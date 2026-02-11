import json
import anthropic
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
from config.brands import BRAND_DEFINITIONS


VALID_BRANDS = {"on24", "goldcast", "zoom", "other"}


class ResponseParser:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def parse_response(self, raw_response_text: str) -> dict:
        system_prompt = """Extract brand mentions from an LLM response about webinar platforms.

Return ONLY a JSON object (no markdown, no explanation) with this exact structure:
{
  "mentions": [
    {"brand": "on24", "position": 1, "context": "sentence about brand", "sentiment": "positive", "sentiment_score": 0.8, "is_primary_recommendation": true},
  ],
  "brands_not_mentioned": ["goldcast"],
  "overall_winner": "on24",
  "zoom_context_is_webinar": true
}

BRAND VALUES (use these exact strings):
- "on24" for ON24
- "goldcast" for Goldcast
- "zoom" for Zoom Webinars/Events (set zoom_context_is_webinar=false if it's about Zoom Meetings)
- "other" for any other brand

RULES:
- position = ordinal (1st mentioned=1, 2nd=2, etc.)
- sentiment = "positive" | "neutral" | "negative"
- sentiment_score = -1.0 to 1.0
- is_primary_recommendation = true if brand is the top/first recommendation
- overall_winner = brand most favorably positioned, or "none"
- brands_not_mentioned = list of on24/goldcast/zoom that are NOT mentioned"""

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": raw_response_text}],
            )

            text = response.content[0].text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            parsed = json.loads(text)
            return self._normalize(parsed)

        except (json.JSONDecodeError, IndexError, KeyError, Exception) as e:
            return {
                "mentions": [],
                "brands_not_mentioned": ["on24", "goldcast", "zoom"],
                "overall_winner": "none",
                "zoom_context_is_webinar": True,
                "parse_error": str(e),
            }

    def _normalize(self, parsed: dict) -> dict:
        mentions_raw = parsed.get("mentions") or parsed.get("brands_mentioned", [])
        normalized = []
        for m in mentions_raw:
            brand = (m.get("brand") or m.get("brand_id") or "other").lower().strip()
            if brand not in VALID_BRANDS:
                # Try to match aliases
                brand = self._resolve_brand(brand)

            normalized.append({
                "brand": brand,
                "position": m.get("position") or m.get("mention_order", 1),
                "context": m.get("context", ""),
                "sentiment": m.get("sentiment", "neutral"),
                "sentiment_score": float(m.get("sentiment_score", 0.0)),
                "is_primary_recommendation": bool(m.get("is_primary_recommendation", False)),
            })

        return {
            "mentions": normalized,
            "brands_not_mentioned": parsed.get("brands_not_mentioned", []),
            "overall_winner": parsed.get("overall_winner", "none"),
            "zoom_context_is_webinar": parsed.get("zoom_context_is_webinar", True),
        }

    @staticmethod
    def _resolve_brand(brand_str: str) -> str:
        brand_str = brand_str.lower().strip()
        for key, defn in BRAND_DEFINITIONS.items():
            if brand_str == key or brand_str in [a.lower() for a in defn["aliases"]]:
                return key
            if defn["display_name"].lower() in brand_str:
                return key
        return "other"

import json
import anthropic
from itertools import groupby
from operator import itemgetter
from config.settings import _get_secret, CLAUDE_MODEL_RECOMMENDATIONS


class RecommendationEngine:
    def __init__(self, db):
        self.db = db
        self.client = anthropic.Anthropic(api_key=_get_secret("ANTHROPIC_API_KEY"))

    def generate_recommendations(self, run_id=None) -> dict:
        data_summary = self._build_data_summary(run_id)

        system_prompt = """You are a senior GEO (Generative Engine Optimization) strategist for B2B marketing technology.
Analyze the benchmark data and provide tactical recommendations to improve ON24's visibility in LLM search results.

Focus on:
1. Which search terms ON24 is winning and losing
2. Content gaps where ON24 is not mentioned but competitors are
3. Specific actions to improve www.on24.com citations (NOT event.on24.com)
4. Tactical content and SEO recommendations

Return a JSON object with this exact structure:
{
  "executive_summary": "string",
  "on24_sov_assessment": "string",
  "wins": [{"query": "string", "reason": "string"}],
  "losses": [{"query": "string", "winning_competitor": "string", "reason": "string"}],
  "recommendations": [{"priority": 1, "category": "string", "action": "string", "rationale": "string", "expected_impact": "high|medium|low"}],
  "competitor_insights": {
    "goldcast": {"strengths": "string", "weaknesses": "string", "threat_level": "high|medium|low"},
    "zoom": {"strengths": "string", "weaknesses": "string", "threat_level": "high|medium|low"}
  }
}"""

        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL_RECOMMENDATIONS,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": f"Analyze this GEO benchmark data:\n\n{data_summary}"}],
            )

            text = response.content[0].text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text)

        except (json.JSONDecodeError, Exception) as e:
            return {
                "executive_summary": f"Error generating recommendations: {e}",
                "on24_sov_assessment": "",
                "wins": [],
                "losses": [],
                "recommendations": [],
                "competitor_insights": {
                    "goldcast": {"strengths": "", "weaknesses": "", "threat_level": "medium"},
                    "zoom": {"strengths": "", "weaknesses": "", "threat_level": "medium"},
                },
            }

    def _build_data_summary(self, run_id=None) -> str:
        if run_id is None:
            run_id = self.db.get_latest_run_id()
        if not run_id:
            return "No benchmark data available yet."

        metrics = self.db.get_daily_metrics_for_run(run_id)
        lines = ["=== GEO BENCHMARK DATA SUMMARY ===\n"]

        sorted_metrics = sorted(metrics, key=itemgetter("query_id"))
        for query_id, group in groupby(sorted_metrics, key=itemgetter("query_id")):
            rows = list(group)
            query_text = self.db.get_query_text(query_id)
            lines.append(f"\nQuery: \"{query_text}\"")
            lines.append(f"Category: {rows[0]['query_category']}")

            for row in rows:
                status = "MENTIONED" if row["is_mentioned"] else "NOT MENTIONED"
                primary = " [PRIMARY]" if row["is_primary_recommendation"] else ""
                winner = " [WINNER]" if row["is_winner"] else ""
                pos = f"Pos#{row['first_mention_position']}" if row["first_mention_position"] else "N/A"
                sent = f"Sent:{row['avg_sentiment_score']:.2f}" if row["avg_sentiment_score"] is not None else ""
                cites = f"Cites:{row['citation_count']}" if row["citation_count"] else ""

                lines.append(
                    f"  [{row['llm_engine']}] {row['brand'].upper()}: "
                    f"{status} | {pos} | {sent} | {cites}{primary}{winner}"
                )

        return "\n".join(lines)

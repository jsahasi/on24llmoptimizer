from urllib.parse import urlparse
from config.brands import BRAND_DEFINITIONS
from config.settings import TRACKED_BRANDS


class MetricsCalculator:
    def __init__(self, db):
        self.db = db

    def compute_daily_metrics(self, run_id: int):
        run = self.db.get_run(run_id)
        run_date = run["run_date"]
        responses = self.db.get_responses_for_run(run_id)

        for resp in responses:
            query_id = resp["query_id"]
            engine = resp["llm_engine"]
            query_category = self.db.get_query_category(query_id)
            mentions = self.db.get_mentions_for_response(resp["id"])
            citations = self.db.get_citations_for_response(resp["id"])

            for brand_key in TRACKED_BRANDS:
                brand_mentions = [m for m in mentions if m["brand"] == brand_key]
                brand_citations = [c for c in citations if c["brand_association"] == brand_key]

                is_mentioned = 1 if brand_mentions else 0
                mention_count = len(brand_mentions)
                first_position = (
                    min(m["mention_position"] for m in brand_mentions)
                    if brand_mentions
                    else None
                )
                is_primary = 1 if any(m["is_primary_recommendation"] for m in brand_mentions) else 0

                avg_sentiment = None
                dominant = None
                if brand_mentions:
                    scores = [m["sentiment_score"] for m in brand_mentions if m["sentiment_score"] is not None]
                    avg_sentiment = sum(scores) / len(scores) if scores else 0.0
                    sentiments = [m["sentiment"] for m in brand_mentions]
                    dominant = max(set(sentiments), key=sentiments.count)

                citation_count = len(brand_citations)
                www_count = sum(1 for c in brand_citations if c["is_on24_www"]) if brand_key == "on24" else 0
                event_count = sum(1 for c in brand_citations if c["is_on24_event"]) if brand_key == "on24" else 0

                self.db.store_daily_metric(
                    run_date=run_date, run_id=run_id, query_id=query_id,
                    query_category=query_category, llm_engine=engine,
                    brand=brand_key, is_mentioned=is_mentioned,
                    mention_count=mention_count,
                    first_mention_position=first_position,
                    is_primary_recommendation=is_primary,
                    avg_sentiment_score=avg_sentiment,
                    dominant_sentiment=dominant,
                    citation_count=citation_count,
                    www_citation_count=www_count,
                    event_citation_count=event_count,
                )

        self._compute_winners(run_id)

    def _compute_winners(self, run_id: int):
        metrics = self.db.get_daily_metrics_for_run(run_id)

        # Group by (query_id, llm_engine)
        groups = {}
        for m in metrics:
            key = (m["query_id"], m["llm_engine"])
            groups.setdefault(key, []).append(m)

        for key, group in groups.items():
            best = None
            best_score = -999
            for m in group:
                if not m["is_mentioned"]:
                    continue
                score = 0
                if m["is_primary_recommendation"]:
                    score += 100
                if m["first_mention_position"]:
                    score += 10 / m["first_mention_position"]
                if m["avg_sentiment_score"] is not None:
                    score += m["avg_sentiment_score"] * 5
                if score > best_score:
                    best_score = score
                    best = m

            if best:
                self.db.set_winner(best["id"])

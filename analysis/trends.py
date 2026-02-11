class TrendAnalyzer:
    def __init__(self, db):
        self.db = db

    def get_sov_trend(self, engine="grok_web_search", days=30):
        return self.db.query(
            """SELECT run_date AS date, brand,
                      ROUND(AVG(is_mentioned) * 100, 1) AS sov
               FROM daily_metrics
               WHERE llm_engine = ? AND run_date >= date('now', ?)
               GROUP BY run_date, brand ORDER BY run_date""",
            (engine, f"-{days} days"),
        )

    def get_position_trend(self, engine="grok_web_search", days=30):
        return self.db.query(
            """SELECT run_date AS date, brand,
                      ROUND(AVG(first_mention_position), 2) AS avg_position
               FROM daily_metrics
               WHERE llm_engine = ? AND run_date >= date('now', ?)
                     AND first_mention_position IS NOT NULL
               GROUP BY run_date, brand ORDER BY run_date""",
            (engine, f"-{days} days"),
        )

    def get_sentiment_trend(self, engine="grok_web_search", days=30):
        return self.db.query(
            """SELECT run_date AS date, brand,
                      ROUND(AVG(avg_sentiment_score), 3) AS sentiment
               FROM daily_metrics
               WHERE llm_engine = ? AND run_date >= date('now', ?)
                     AND avg_sentiment_score IS NOT NULL
               GROUP BY run_date, brand ORDER BY run_date""",
            (engine, f"-{days} days"),
        )

    def get_win_rate_trend(self, engine="grok_web_search", days=30):
        return self.db.query(
            """SELECT run_date AS date, brand,
                      ROUND(AVG(is_winner) * 100, 1) AS win_rate
               FROM daily_metrics
               WHERE llm_engine = ? AND run_date >= date('now', ?)
               GROUP BY run_date, brand ORDER BY run_date""",
            (engine, f"-{days} days"),
        )

    def get_citation_trend(self, engine="grok_web_search", days=30):
        return self.db.query(
            """SELECT run_date AS date, brand,
                      SUM(citation_count) AS total_citations,
                      SUM(www_citation_count) AS www_citations,
                      SUM(event_citation_count) AS event_citations
               FROM daily_metrics
               WHERE llm_engine = ? AND run_date >= date('now', ?)
               GROUP BY run_date, brand ORDER BY run_date""",
            (engine, f"-{days} days"),
        )

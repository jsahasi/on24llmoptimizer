import os
import json
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
from config.settings import DB_PATH
from config.brands import BRAND_DEFINITIONS


class DatabaseManager:
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        conn = self._get_conn()
        conn.executescript(schema_sql)
        conn.close()

    def query(self, sql, params=None):
        conn = self._get_conn()
        cursor = conn.execute(sql, params or ())
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def execute(self, sql, params=None):
        conn = self._get_conn()
        cursor = conn.execute(sql, params or ())
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def executemany(self, sql, params_list):
        conn = self._get_conn()
        conn.executemany(sql, params_list)
        conn.commit()
        conn.close()

    # --- Queries ---
    def seed_queries(self, query_library):
        conn = self._get_conn()
        for q in query_library:
            conn.execute(
                "INSERT OR IGNORE INTO queries (query_text, category, subcategory) VALUES (?, ?, ?)",
                (q["query_text"], q["category"], q.get("subcategory")),
            )
        conn.commit()
        conn.close()

    def get_active_queries(self):
        return self.query("SELECT * FROM queries WHERE is_active = 1 ORDER BY id")

    def get_query_text(self, query_id):
        rows = self.query("SELECT query_text FROM queries WHERE id = ?", (query_id,))
        return rows[0]["query_text"] if rows else None

    def get_query_category(self, query_id):
        rows = self.query("SELECT category FROM queries WHERE id = ?", (query_id,))
        return rows[0]["category"] if rows else None

    # --- Benchmark Runs ---
    def create_run(self, run_date, total_queries, trigger_type="manual"):
        return self.execute(
            "INSERT INTO benchmark_runs (run_date, started_at, total_queries, trigger_type) VALUES (?, ?, ?, ?)",
            (run_date, datetime.now().isoformat(), total_queries, trigger_type),
        )

    def get_run(self, run_id):
        rows = self.query("SELECT * FROM benchmark_runs WHERE id = ?", (run_id,))
        return rows[0] if rows else None

    def get_latest_run_id(self):
        rows = self.query(
            "SELECT id FROM benchmark_runs WHERE status = 'completed' ORDER BY id DESC LIMIT 1"
        )
        return rows[0]["id"] if rows else None

    def update_run_progress(self, run_id, completed_queries):
        self.execute(
            "UPDATE benchmark_runs SET completed_queries = ? WHERE id = ?",
            (completed_queries, run_id),
        )

    def complete_run(self, run_id):
        self.execute(
            "UPDATE benchmark_runs SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.now().isoformat(), run_id),
        )

    def fail_run(self, run_id, error_message):
        self.execute(
            "UPDATE benchmark_runs SET status = 'failed', completed_at = ?, error_message = ? WHERE id = ?",
            (datetime.now().isoformat(), error_message, run_id),
        )

    def log_error(self, run_id, query_id, engine, error_msg):
        """Log an error for a specific query without failing the entire run."""
        self.execute(
            """INSERT INTO responses (run_id, query_id, llm_engine, model_name, raw_response, response_metadata)
               VALUES (?, ?, ?, 'error', '', ?)""",
            (run_id, query_id, engine, json.dumps({"error": error_msg})),
        )

    # --- Responses ---
    def store_response(self, run_id, query_id, llm_engine, model_name, raw_response, metadata=None):
        return self.execute(
            """INSERT INTO responses (run_id, query_id, llm_engine, model_name, raw_response, response_metadata)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (run_id, query_id, llm_engine, model_name, raw_response, json.dumps(metadata) if metadata else None),
        )

    def get_responses_for_run(self, run_id):
        return self.query(
            "SELECT * FROM responses WHERE run_id = ? AND model_name != 'error' ORDER BY id",
            (run_id,),
        )

    # --- Mentions ---
    def store_mention(self, response_id, run_id, query_id, brand, mention_position,
                      mention_context, sentiment, sentiment_score, is_primary, llm_engine):
        return self.execute(
            """INSERT INTO mentions (response_id, run_id, query_id, brand, mention_position,
               mention_context, sentiment, sentiment_score, is_primary_recommendation, llm_engine)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (response_id, run_id, query_id, brand, mention_position,
             mention_context, sentiment, sentiment_score, 1 if is_primary else 0, llm_engine),
        )

    def get_mentions_for_response(self, response_id):
        return self.query("SELECT * FROM mentions WHERE response_id = ?", (response_id,))

    # --- Citations ---
    def store_citation(self, response_id, run_id, query_id, url, title, llm_engine):
        classification = self._classify_citation_domain(url)
        return self.execute(
            """INSERT INTO citations (response_id, run_id, query_id, url, url_domain,
               title, brand_association, is_on24_www, is_on24_event, llm_engine)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (response_id, run_id, query_id, url, classification["url_domain"],
             title, classification["brand_association"],
             classification["is_on24_www"], classification["is_on24_event"], llm_engine),
        )

    def get_citations_for_response(self, response_id):
        return self.query("SELECT * FROM citations WHERE response_id = ?", (response_id,))

    @staticmethod
    def _classify_citation_domain(url):
        parsed = urlparse(url)
        domain = parsed.netloc.lower().lstrip("www.") if parsed.netloc else ""
        full_domain = parsed.netloc.lower() if parsed.netloc else ""

        result = {
            "url_domain": full_domain,
            "brand_association": "other",
            "is_on24_www": 0,
            "is_on24_event": 0,
        }

        if "on24.com" in domain:
            result["brand_association"] = "on24"
            if "event.on24.com" in full_domain:
                result["is_on24_event"] = 1
            else:
                result["is_on24_www"] = 1
        elif "goldcast.io" in domain:
            result["brand_association"] = "goldcast"
        elif "zoom.us" in domain:
            result["brand_association"] = "zoom"

        return result

    # --- Daily Metrics ---
    def store_daily_metric(self, **kwargs):
        return self.execute(
            """INSERT OR REPLACE INTO daily_metrics
               (run_date, run_id, query_id, query_category, llm_engine, brand,
                is_mentioned, mention_count, first_mention_position,
                is_primary_recommendation, avg_sentiment_score, dominant_sentiment,
                citation_count, www_citation_count, event_citation_count, is_winner)
               VALUES (:run_date, :run_id, :query_id, :query_category, :llm_engine, :brand,
                :is_mentioned, :mention_count, :first_mention_position,
                :is_primary_recommendation, :avg_sentiment_score, :dominant_sentiment,
                :citation_count, :www_citation_count, :event_citation_count, 0)""",
            kwargs,
        )

    def get_daily_metrics_for_run(self, run_id):
        return self.query("SELECT * FROM daily_metrics WHERE run_id = ?", (run_id,))

    def set_winner(self, metric_id):
        self.execute("UPDATE daily_metrics SET is_winner = 1 WHERE id = ?", (metric_id,))

    # --- Aggregation queries for dashboard ---
    def get_latest_sov(self, engine="grok_web_search"):
        run_id = self.get_latest_run_id()
        if not run_id:
            return []
        return self.query(
            """SELECT brand,
                      ROUND(AVG(is_mentioned) * 100, 1) AS sov,
                      ROUND(AVG(first_mention_position), 2) AS avg_position,
                      ROUND(AVG(avg_sentiment_score), 3) AS avg_sentiment,
                      ROUND(AVG(is_winner) * 100, 1) AS win_rate
               FROM daily_metrics
               WHERE run_id = ? AND llm_engine = ?
               GROUP BY brand""",
            (run_id, engine),
        )

    def get_search_term_breakdown(self, run_id=None, engine="grok_web_search"):
        if run_id is None:
            run_id = self.get_latest_run_id()
        if not run_id:
            return []
        return self.query(
            """SELECT dm.query_id, q.query_text, q.category, dm.brand,
                      dm.is_mentioned, dm.first_mention_position,
                      dm.avg_sentiment_score, dm.is_primary_recommendation,
                      dm.is_winner
               FROM daily_metrics dm
               JOIN queries q ON q.id = dm.query_id
               WHERE dm.run_id = ? AND dm.llm_engine = ?
               ORDER BY q.id, dm.brand""",
            (run_id, engine),
        )

    def get_all_runs(self):
        return self.query("SELECT * FROM benchmark_runs ORDER BY id DESC")

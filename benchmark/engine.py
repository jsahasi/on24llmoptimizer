import datetime
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.database import DatabaseManager
from benchmark.grok_client import GrokWebSearchClient
from benchmark.claude_client import ClaudeParametricClient
from benchmark.openai_client import OpenAISearchClient
from analysis.parser import ResponseParser
from analysis.metrics import MetricsCalculator
from config.queries import QUERY_LIBRARY

logger = logging.getLogger(__name__)

ENGINES = ["grok_web_search", "chatgpt_web_search", "claude_parametric"]

# Per-engine rate limiting (seconds between requests per engine)
ENGINE_DELAYS = {
    "grok_web_search": 2.5,
    "chatgpt_web_search": 1.5,
    "claude_parametric": 1.5,
}


class _RateLimiter:
    """Thread-safe per-engine rate limiter."""
    def __init__(self):
        self._locks = {eng: threading.Lock() for eng in ENGINES}
        self._last_call = {eng: 0.0 for eng in ENGINES}

    def wait(self, engine_name):
        with self._locks[engine_name]:
            delay = ENGINE_DELAYS.get(engine_name, 1.5)
            elapsed = time.time() - self._last_call[engine_name]
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_call[engine_name] = time.time()


class BenchmarkEngine:
    def __init__(self, trigger_type="manual"):
        self.db = DatabaseManager()
        self.grok = GrokWebSearchClient()
        self.claude = ClaudeParametricClient()
        self.openai = OpenAISearchClient()
        self.parser = ResponseParser()
        self.metrics = MetricsCalculator(self.db)
        self.trigger_type = trigger_type
        self._clients = {
            "grok_web_search": self.grok,
            "chatgpt_web_search": self.openai,
            "claude_parametric": self.claude,
        }
        self._rate_limiter = _RateLimiter()

    def _get_completed_pairs(self, run_id):
        """Return set of (query_id, engine) pairs already completed for this run."""
        rows = self.db.query(
            "SELECT query_id, llm_engine FROM responses WHERE run_id = ? AND model_name != 'error'",
            (run_id,),
        )
        return {(r["query_id"], r["llm_engine"]) for r in rows}

    def _run_single(self, run_id, qid, qtxt, engine_name):
        """Execute a single (query, engine) pair. Thread-safe."""
        label = {"grok_web_search": "Grok", "chatgpt_web_search": "ChatGPT", "claude_parametric": "Claude"}[engine_name]
        try:
            self._rate_limiter.wait(engine_name)
            client = self._clients[engine_name]
            result = client.query(qtxt)

            # Use a dedicated DB connection per thread
            db = DatabaseManager()
            resp_id = db.store_response(
                run_id=run_id, query_id=qid, llm_engine=engine_name,
                model_name=result["model"], raw_response=result["raw_response"],
                metadata=result["usage"],
            )

            parsed = self.parser.parse_response(result["raw_response"])
            for mention in parsed.get("mentions", []):
                db.store_mention(
                    response_id=resp_id, run_id=run_id, query_id=qid,
                    brand=mention["brand"], mention_position=mention["position"],
                    mention_context=mention["context"], sentiment=mention["sentiment"],
                    sentiment_score=mention["sentiment_score"],
                    is_primary=mention["is_primary_recommendation"],
                    llm_engine=engine_name,
                )
            for citation in result.get("citations", []):
                if citation.get("url"):
                    db.store_citation(
                        response_id=resp_id, run_id=run_id, query_id=qid,
                        url=citation["url"], title=citation.get("title", ""),
                        llm_engine=engine_name,
                    )

            return {"status": "ok", "engine": label, "query_id": qid}

        except Exception as e:
            logger.error(f"{label} error for query {qid}: {e}")
            try:
                db = DatabaseManager()
                db.log_error(run_id, qid, engine_name, str(e))
            except Exception:
                pass
            return {"status": f"error: {str(e)[:80]}", "engine": label, "query_id": qid, "error": str(e)}

    def run(self, progress_callback=None, run_id=None, max_workers=9) -> int:
        """Run the benchmark with parallel execution.

        max_workers=9 means up to 3 queries x 3 engines running concurrently.
        If run_id is provided, resume that run (skipping completed pairs).
        """
        self.db.seed_queries(QUERY_LIBRARY)
        active_queries = self.db.get_active_queries()

        if run_id is None:
            run_id = self.db.create_run(
                run_date=datetime.date.today().isoformat(),
                total_queries=len(active_queries),
                trigger_type=self.trigger_type,
            )

        completed = self._get_completed_pairs(run_id)

        # Build work items: all (query, engine) pairs not yet completed
        work_items = []
        for query in active_queries:
            for engine_name in ENGINES:
                if (query["id"], engine_name) not in completed:
                    work_items.append((query["id"], query["query_text"], engine_name))

        total_steps = len(active_queries) * len(ENGINES)
        done_count = len(completed)

        if not work_items:
            # Everything already done, just compute metrics
            self.metrics.compute_daily_metrics(run_id)
            self.db.complete_run(run_id)
            return run_id

        if progress_callback:
            progress_callback(done_count, total_steps, f"Starting {len(work_items)} tasks ({max_workers} parallel)...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._run_single, run_id, qid, qtxt, eng): (qid, eng)
                for qid, qtxt, eng in work_items
            }

            for future in as_completed(futures):
                done_count += 1
                result = future.result()
                label = result.get("engine", "?")
                qid = result.get("query_id", "?")
                status = result.get("status", "?")

                if progress_callback:
                    progress_callback(
                        done_count, total_steps,
                        f"[{done_count}/{total_steps}] {label} q{qid}: {status}"
                    )

                # Update progress every few completions
                if done_count % 3 == 0:
                    self.db.update_run_progress(run_id, completed_queries=done_count // len(ENGINES))

        self.db.update_run_progress(run_id, completed_queries=len(active_queries))
        self.metrics.compute_daily_metrics(run_id)
        self.db.complete_run(run_id)

        return run_id

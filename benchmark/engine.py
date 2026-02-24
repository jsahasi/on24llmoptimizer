import datetime
import logging
from db.database import DatabaseManager
from benchmark.grok_client import GrokWebSearchClient
from benchmark.claude_client import ClaudeParametricClient
from benchmark.openai_client import OpenAISearchClient
from analysis.parser import ResponseParser
from analysis.metrics import MetricsCalculator
from config.queries import QUERY_LIBRARY

logger = logging.getLogger(__name__)

ENGINES = ["grok_web_search", "chatgpt_web_search", "claude_parametric"]


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

    def _get_completed_pairs(self, run_id):
        """Return set of (query_id, engine) pairs already completed for this run."""
        rows = self.db.query(
            "SELECT query_id, llm_engine FROM responses WHERE run_id = ? AND model_name != 'error'",
            (run_id,),
        )
        return {(r["query_id"], r["llm_engine"]) for r in rows}

    def run(self, progress_callback=None, run_id=None) -> int:
        """Run the benchmark. If run_id is provided, resume that run."""
        self.db.seed_queries(QUERY_LIBRARY)
        active_queries = self.db.get_active_queries()

        if run_id is None:
            run_id = self.db.create_run(
                run_date=datetime.date.today().isoformat(),
                total_queries=len(active_queries),
                trigger_type=self.trigger_type,
            )

        completed = self._get_completed_pairs(run_id)
        total_steps = len(active_queries) * len(ENGINES)
        current_step = len(completed)

        try:
            for query in active_queries:
                qid = query["id"]
                qtxt = query["query_text"]

                for engine_name in ENGINES:
                    if (qid, engine_name) in completed:
                        continue  # Already done, skip

                    label = {"grok_web_search": "Grok", "chatgpt_web_search": "ChatGPT", "claude_parametric": "Claude"}[engine_name]
                    if progress_callback:
                        progress_callback(current_step, total_steps, f"{label}: {qtxt[:55]}...")

                    try:
                        client = self._clients[engine_name]
                        result = client.query(qtxt)
                        resp_id = self.db.store_response(
                            run_id=run_id, query_id=qid, llm_engine=engine_name,
                            model_name=result["model"], raw_response=result["raw_response"],
                            metadata=result["usage"],
                        )
                        self._parse_and_store(resp_id, run_id, qid, result, engine_name)
                    except Exception as e:
                        logger.error(f"{label} error for query {qid}: {e}")
                        self.db.log_error(run_id, qid, engine_name, str(e))

                    current_step += 1

                self.db.update_run_progress(run_id, completed_queries=current_step // len(ENGINES))

            # Compute aggregated metrics
            self.metrics.compute_daily_metrics(run_id)
            self.db.complete_run(run_id)

        except Exception as e:
            # Don't fail the run — leave it as "running" so it can be resumed
            logger.error(f"Benchmark interrupted: {e}")
            raise

        return run_id

    def _parse_and_store(self, response_id, run_id, query_id, result, engine):
        parsed = self.parser.parse_response(result["raw_response"])

        for mention in parsed.get("mentions", []):
            self.db.store_mention(
                response_id=response_id, run_id=run_id, query_id=query_id,
                brand=mention["brand"], mention_position=mention["position"],
                mention_context=mention["context"], sentiment=mention["sentiment"],
                sentiment_score=mention["sentiment_score"],
                is_primary=mention["is_primary_recommendation"],
                llm_engine=engine,
            )

        for citation in result.get("citations", []):
            if citation.get("url"):
                self.db.store_citation(
                    response_id=response_id, run_id=run_id, query_id=query_id,
                    url=citation["url"], title=citation.get("title", ""),
                    llm_engine=engine,
                )

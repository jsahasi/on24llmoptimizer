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


class BenchmarkEngine:
    def __init__(self, trigger_type="manual"):
        self.db = DatabaseManager()
        self.grok = GrokWebSearchClient()
        self.claude = ClaudeParametricClient()
        self.openai = OpenAISearchClient()
        self.parser = ResponseParser()
        self.metrics = MetricsCalculator(self.db)
        self.trigger_type = trigger_type

    def run(self, progress_callback=None) -> int:
        self.db.seed_queries(QUERY_LIBRARY)
        active_queries = self.db.get_active_queries()

        run_id = self.db.create_run(
            run_date=datetime.date.today().isoformat(),
            total_queries=len(active_queries),
            trigger_type=self.trigger_type,
        )

        total_steps = len(active_queries) * 3  # 3 engines per query
        current_step = 0

        try:
            for query in active_queries:
                qid = query["id"]
                qtxt = query["query_text"]

                # --- Grok Web Search ---
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Grok: {qtxt[:60]}...")
                try:
                    result = self.grok.query(qtxt)
                    resp_id = self.db.store_response(
                        run_id=run_id, query_id=qid, llm_engine="grok_web_search",
                        model_name=result["model"], raw_response=result["raw_response"],
                        metadata=result["usage"],
                    )
                    self._parse_and_store(resp_id, run_id, qid, result, "grok_web_search")
                except Exception as e:
                    logger.error(f"Grok error for query {qid}: {e}")
                    self.db.log_error(run_id, qid, "grok_web_search", str(e))
                current_step += 1

                # --- OpenAI ChatGPT Web Search ---
                if progress_callback:
                    progress_callback(current_step, total_steps, f"ChatGPT: {qtxt[:60]}...")
                try:
                    result = self.openai.query(qtxt)
                    resp_id = self.db.store_response(
                        run_id=run_id, query_id=qid, llm_engine="chatgpt_web_search",
                        model_name=result["model"], raw_response=result["raw_response"],
                        metadata=result["usage"],
                    )
                    self._parse_and_store(resp_id, run_id, qid, result, "chatgpt_web_search")
                except Exception as e:
                    logger.error(f"ChatGPT error for query {qid}: {e}")
                    self.db.log_error(run_id, qid, "chatgpt_web_search", str(e))
                current_step += 1

                # --- Claude Parametric ---
                if progress_callback:
                    progress_callback(current_step, total_steps, f"Claude: {qtxt[:60]}...")
                try:
                    result = self.claude.query(qtxt)
                    resp_id = self.db.store_response(
                        run_id=run_id, query_id=qid, llm_engine="claude_parametric",
                        model_name=result["model"], raw_response=result["raw_response"],
                        metadata=result["usage"],
                    )
                    self._parse_and_store(resp_id, run_id, qid, result, "claude_parametric")
                except Exception as e:
                    logger.error(f"Claude error for query {qid}: {e}")
                    self.db.log_error(run_id, qid, "claude_parametric", str(e))
                current_step += 1

                self.db.update_run_progress(run_id, completed_queries=current_step // 3)

            # Compute aggregated metrics
            self.metrics.compute_daily_metrics(run_id)
            self.db.complete_run(run_id)

        except Exception as e:
            self.db.fail_run(run_id, str(e))
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

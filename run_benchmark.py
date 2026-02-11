"""Standalone script for Windows Task Scheduler. Runs a full benchmark and exits."""
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.makedirs(os.path.join(os.path.dirname(__file__), "logs"), exist_ok=True)

logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), "logs", "benchmark.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    logging.info("=== Scheduled benchmark starting ===")
    try:
        from benchmark.engine import BenchmarkEngine

        engine = BenchmarkEngine(trigger_type="scheduled")
        run_id = engine.run()
        logging.info(f"Benchmark completed. Run ID: {run_id}")
        print(f"Benchmark completed. Run ID: {run_id}")
    except Exception as e:
        logging.error(f"Benchmark failed: {e}", exc_info=True)
        print(f"Benchmark failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

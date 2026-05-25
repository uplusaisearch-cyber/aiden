"""Topic Newsroom 실제 LLM 실행 스크립트.

사용법:
    python scripts/run_topic_newsroom_live.py --category 맛집

실행 후 ``runs/{timestamp}_{run_id}/`` 폴더에 trace 생성됨.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path 에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from backend.agents.concrete_agents import build_topic_newsroom_agents  # noqa: E402
from backend.llm.gemini_client import GeminiClient  # noqa: E402
from backend.orchestrators.topic_newsroom import TopicNewsroom  # noqa: E402
from backend.orchestrators.trace_logger import TraceLogger  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("topic_newsroom_live")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="콘텐츠 카테고리")
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()

    # Gemini 클라이언트
    client = GeminiClient(model=args.model)

    # 에이전트 callable
    agents = build_topic_newsroom_agents(client)

    # Tracer
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"Run started: {tracer.run_dir}")

    # Topic Newsroom 실행
    tn = TopicNewsroom(
        tracer=tracer,
        scout_fn=agents["scout"],
        analyst_fn=agents["analyst"],
        planner_fn=agents["planner"],
    )

    try:
        result = tn.run(category=args.category)
        status = "completed" if "final_topic" in result else "partial"
    except Exception as e:
        logger.exception("Topic Newsroom 실행 중 예외 발생")
        result = {"error": str(e)}
        status = "failed"

    tracer.write_metadata(
        user_input={"category": args.category, "model": args.model},
        status=status,
        notes="Step 2.5 조기 LLM 통합 실험",
    )

    logger.info(f"Run finished: {tracer.run_dir}")
    logger.info(f"Status: {status}")
    if "final_topic" in result:
        logger.info(f"Final title: {result['final_topic'].get('title')}")


if __name__ == "__main__":
    main()

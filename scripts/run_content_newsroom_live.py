"""Content Newsroom 실제 LLM 실행 스크립트 (iter 1만).

사용법: Topic Newsroom 결과의 final_topic JSON 을 파일로 받음

    python scripts/run_content_newsroom_live.py --topic-file runs/<run_id>/agents/03_strategy_planner.json

실행 후 ``runs/{timestamp}_{run_id}/`` 폴더에 trace 생성됨.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from backend.agents.concrete_agents import build_content_newsroom_agents  # noqa: E402
from backend.llm.gemini_client import GeminiClient  # noqa: E402
from backend.orchestrators.content_newsroom import ContentNewsroom  # noqa: E402
from backend.orchestrators.trace_logger import TraceLogger  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("content_newsroom_live")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic-file",
        required=True,
        help="Strategy Planner 출력 JSON 파일 경로 (trace 폴더의 03_strategy_planner.json)",
    )
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()

    # Strategy Planner 출력 로드
    topic_data = json.loads(Path(args.topic_file).read_text(encoding="utf-8"))

    # trace 파일 구조에서 output 을 추출
    if "output" in topic_data:
        planner_output = topic_data["output"]
    else:
        planner_output = topic_data

    if "final_topic" not in planner_output:
        logger.error("입력 파일에 final_topic 없음. Topic Newsroom 결과 파일을 사용하세요.")
        sys.exit(1)

    final_topic = planner_output["final_topic"]
    category = final_topic.get("category", "기타")

    # Gemini 클라이언트
    client = GeminiClient(model=args.model)

    # 에이전트 callable
    agents = build_content_newsroom_agents(client)

    # Tracer
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"Run started: {tracer.run_dir}")

    # Content Newsroom 실행 (iter 1만 검증 목적)
    # 실제로는 max 3 iter 지만 본 스크립트는 흐름 검증용
    cn = ContentNewsroom(
        tracer=tracer,
        writer_fn=agents["writer"],
        fact_checker_fn=agents["fact_checker"],
        devils_advocate_fn=agents["devils_advocate"],
        editor_fn=agents["editor"],
        base_order=4,
    )

    try:
        result = cn.run(category=category, strategy=final_topic)
        status = "completed" if result.get("decision") == "approved" else "partial"
    except Exception as e:
        logger.exception("Content Newsroom 실행 중 예외 발생")
        result = {"error": str(e)}
        status = "failed"

    tracer.write_metadata(
        user_input={"category": category, "topic_file": args.topic_file, "model": args.model},
        status=status,
        notes="Step 2.5 조기 LLM 통합 실험 - Content Newsroom",
    )

    logger.info(f"Run finished: {tracer.run_dir}")
    logger.info(f"Status: {status}")
    if "final_content" in result:
        logger.info(f"Final title: {result['final_content'].get('title')}")
        logger.info(f"Iterations used: {result.get('iteration')}")
        logger.info(f"Forced: {result.get('_orchestrator_forced', False)}")


if __name__ == "__main__":
    main()

"""AIDEN 전체 파이프라인 실행 스크립트 (E2E).

사용법:
    python scripts/run_full_pipeline.py --category 맛집

실행 후 ``runs/<timestamp>_<run_id>/`` 폴더에:

- ``agents/01~09_*.json`` (9개 trace)
- ``summary.jsonl``
- ``metadata.json``
- ``final_output.html`` ← 브라우저로 열어 확인
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from backend.agents.concrete_agents import build_all_agents  # noqa: E402
from backend.llm.gemini_client import GeminiClient  # noqa: E402
from backend.orchestrators.full_pipeline import FullPipeline  # noqa: E402
from backend.orchestrators.trace_logger import TraceLogger  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("full_pipeline")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="콘텐츠 카테고리")
    parser.add_argument("--model", default="gemini-2.5-flash")
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="Stage 4 Judge Panel 건너뜀 (디버깅용. 기본은 활성).",
    )
    args = parser.parse_args()

    # Gemini 클라이언트
    client = GeminiClient(model=args.model)

    # 9개 에이전트 callable
    agents = build_all_agents(client)

    # Tracer (Stage 공유)
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"E2E run started: {tracer.run_dir}")

    # Stage 4: Judge Panel (옵션)
    judge_panel = None
    if not args.skip_judge:
        try:
            from backend.orchestrators.judge_panel import JudgePanel
            judge_panel = JudgePanel.from_settings()
            logger.info("Judge Panel 활성: %s", judge_panel.config.get("models"))
        except Exception as e:  # noqa: BLE001
            logger.warning("Judge Panel 비활성화 (초기화 실패): %s", e)
            judge_panel = None
    else:
        logger.info("--skip-judge 지정. Stage 4 건너뜀.")

    # Full Pipeline 실행
    pipeline = FullPipeline(tracer=tracer, agents=agents, judge_panel=judge_panel)

    try:
        result = pipeline.run(category=args.category)
    except Exception as e:
        logger.exception("FullPipeline 실행 중 예외")
        result = {"status": "exception", "error": str(e)}

    # final_output.html 저장
    final_html = result.get("final_html")
    if final_html:
        html_path = tracer.run_dir / "final_output.html"
        # 스탠드얼론 HTML 래퍼 (브라우저 직접 열기용)
        wrapped = (
            "<!DOCTYPE html>\n"
            '<html lang="ko"><head><meta charset="utf-8">'
            f"<title>{args.category} - AIDEN 산출물</title>"
            "<style>"
            "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
            "max-width:680px;margin:0 auto;padding:20px;line-height:1.7;color:#222;}"
            "h1{font-size:24px;}h2{font-size:18px;margin-top:32px;}"
            ".sources{margin-top:32px;padding:16px;background:#f7f7f7;border-radius:8px;}"
            ".known-weaknesses{margin-top:16px;padding:16px;background:#fff4f4;"
            "border-left:4px solid #c00;}"
            "</style></head><body>\n"
            f"{final_html}\n"
            "</body></html>"
        )
        html_path.write_text(wrapped, encoding="utf-8")
        logger.info(f"Final HTML saved: {html_path}")

    # metadata 작성 (Stage 4 결과 병합)
    tracer.write_metadata(
        user_input={
            "category": args.category,
            "model": args.model,
            "skip_judge": args.skip_judge,
        },
        status=result.get("status", "unknown"),
        notes="B3-S2 E2E (9 에이전트 + Judge Panel)",
        judge_panel=result.get("stage_4"),
    )

    # 요약 로그
    logger.info("=== E2E Run Summary ===")
    logger.info(f"Run dir: {tracer.run_dir}")
    logger.info(f"Status: {result.get('status')}")

    stage_1 = result.get("stage_1") or {}
    stage_2 = result.get("stage_2") or {}
    stage_3 = result.get("stage_3") or {}

    if "final_topic" in stage_1:
        logger.info(f"Stage 1 title: {stage_1['final_topic'].get('title')}")
    if "final_content" in stage_2:
        logger.info(f"Stage 2 iteration: {stage_2.get('iteration')}")
        logger.info(f"Stage 2 forced: {stage_2.get('_orchestrator_forced', False)}")
    if stage_3.get("format_decision"):
        logger.info(f"Stage 3 type: {stage_3['format_decision'].get('selected_type')}")

    if final_html:
        logger.info(f"HTML output: {tracer.run_dir / 'final_output.html'}")
        logger.info("브라우저에서 위 파일을 열어 검증하세요.")


if __name__ == "__main__":
    main()

"""백그라운드 FullPipeline 실행 매니저.

명세: docs/patches/2026-05-25_bundle3_step3_B_fastapi_sse_backend.md

핵심:
- POST /api/generate 에서 호출 → 즉시 session_id 반환, 백그라운드에서 FullPipeline 실행
- FullPipeline.run() 은 sync 이므로 ``asyncio.to_thread`` 로 별도 스레드 가동
- TraceLogger 에 sse_broker + main_loop 주입 → 매 agent step 마다 SSE publish
- 완료/실패 시 pipeline_complete 또는 error 이벤트 publish 후 broker close
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from backend.agents.concrete_agents import build_all_agents
from backend.api.services.sse_broker import SSEBroker
from backend.llm.gemini_client import GeminiClient
from backend.orchestrators.full_pipeline import FullPipeline
from backend.orchestrators.trace_logger import TraceLogger

logger = logging.getLogger(__name__)

CATEGORY_LABEL: dict[str, str] = {
    "food": "맛집",
    "ai-trend": "AI트렌드",
    "safety": "안전",
    "culture": "문화",
    "custom": "자유 입력",
}

PIPELINE_TIMEOUT_SEC = 20 * 60  # 20분


def _apply_standalone_html_wrapper(category: str, final_html: str) -> str:
    # NOTE: must produce byte-identical output with scripts/run_full_pipeline.py wrapper.
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ko"><head><meta charset="utf-8">'
        f"<title>{category} - AIDEN 산출물</title>"
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


def make_session_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{ts}_{uuid4().hex[:8]}"


class RunManager:
    """asyncio.Task 로 FullPipeline 실행을 관리.

    한 프로세스 내 여러 run 동시 지원. 외부 큐/Celery 없이 인-프로세스 백그라운드.
    """

    def __init__(self, sse_broker: SSEBroker, runs_base_dir: str = "runs") -> None:
        self._sse_broker = sse_broker
        self._runs_base_dir = runs_base_dir
        self._active: dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    async def start_run(
        self,
        *,
        category: str,
        custom_topic: str | None = None,
        options: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str:
        """run 을 백그라운드로 시작하고 session_id 반환."""
        opts = options or {}
        sid = session_id or make_session_id()
        loop = asyncio.get_running_loop()
        task = loop.create_task(
            self._execute(sid, category, custom_topic, opts, loop),
            name=f"aiden-run-{sid}",
        )
        self._active[sid] = task
        task.add_done_callback(lambda _t: self._active.pop(sid, None))
        return sid

    def active_session_ids(self) -> list[str]:
        return list(self._active.keys())

    def active_count(self) -> int:
        return len(self._active)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    async def _execute(
        self,
        session_id: str,
        category: str,
        custom_topic: str | None,
        options: dict[str, Any],
        main_loop: asyncio.AbstractEventLoop,
    ) -> None:
        skip_judge = bool(options.get("skip_judge"))
        started_at = datetime.now(timezone.utc)

        # 즉시 시작 알림 (SSE 첫 이벤트)
        await self._sse_broker.publish(
            session_id,
            "pipeline_start",
            {
                "session_id": session_id,
                "category": category,
                "custom_topic": custom_topic,
                "options": options,
                "started_at": started_at.isoformat(),
            },
        )

        try:
            await asyncio.wait_for(
                self._run_pipeline(session_id, category, custom_topic, skip_judge, main_loop),
                timeout=PIPELINE_TIMEOUT_SEC,
            )
            # _run_pipeline 안에서 pipeline_complete 발행됨
        except asyncio.TimeoutError:
            logger.error("Pipeline timeout: %s", session_id)
            await self._sse_broker.publish(
                session_id, "error",
                {"error_message": f"timeout >{PIPELINE_TIMEOUT_SEC}s", "is_recoverable": False},
            )
        except Exception as e:  # noqa: BLE001
            logger.exception("Pipeline 예외: %s", session_id)
            await self._sse_broker.publish(
                session_id, "error",
                {"error_message": str(e), "is_recoverable": False},
            )
        finally:
            await self._sse_broker.close(session_id)

    async def _run_pipeline(
        self,
        session_id: str,
        category: str,
        custom_topic: str | None,
        skip_judge: bool,
        main_loop: asyncio.AbstractEventLoop,
    ) -> None:
        # tracer + agents + judge_panel 준비
        tracer = TraceLogger.new_run(
            base_dir=self._runs_base_dir,
            sse_broker=self._sse_broker,
            main_loop=main_loop,
            session_id=session_id,
        )
        # 모델 체인은 GeminiClient default 또는 AIDEN_GEMINI_MODELS 환경변수 사용.
        # 503 만성 시 자동 폴백 (gemini-2.5-flash → gemini-2.5-flash-lite).
        client = GeminiClient()
        agents = build_all_agents(client)

        judge_panel = None
        if not skip_judge:
            try:
                # lazy import (judge_panel 모듈에 await import 비용)
                from backend.orchestrators.judge_panel import JudgePanel
                judge_panel = JudgePanel.from_settings()
            except Exception as e:  # noqa: BLE001
                logger.warning("Judge Panel 비활성화 (초기화 실패): %s", e)

        pipeline = FullPipeline(tracer=tracer, agents=agents, judge_panel=judge_panel)

        # FullPipeline.run() 은 sync → 별도 스레드로
        target_category_label = CATEGORY_LABEL.get(category, category)
        if category == "custom" and custom_topic:
            # custom 카테고리는 자유 입력. 현재 pipeline 은 카테고리 문자열을 그대로 전달
            target_category_label = custom_topic

        result = await asyncio.to_thread(pipeline.run, target_category_label)

        # final_output.html 저장 (Judge Panel 평가·iframe 미리보기에 필수)
        # CLI scripts/run_full_pipeline.py 과 결과 동일해야 함 (수동 diff 로 검증).
        final_html = result.get("final_html")
        if final_html:
            try:
                final_path = tracer.run_dir / "final_output.html"
                final_path.write_text(
                    _apply_standalone_html_wrapper(target_category_label, final_html),
                    encoding="utf-8",
                )
                logger.info("final_output.html 저장: %s", final_path)
            except OSError as e:
                logger.error("final_output.html 저장 실패: %s", e)

        # metadata 기록 + Stage 4 결과 병합
        tracer.write_metadata(
            user_input={
                "category": category,
                "custom_topic": custom_topic,
                "skip_judge": skip_judge,
            },
            status=result.get("status", "unknown"),
            notes="B3-S3-B API 트리거",
            judge_panel=result.get("stage_4"),
        )

        # 완료 이벤트
        judge_summary = None
        stage_4 = result.get("stage_4") or {}
        if stage_4:
            agg = (stage_4.get("aggregate") or {})
            judge_summary = {
                "status": stage_4.get("status"),
                "weighted_total": agg.get("weighted_total"),
                "outliers": len(agg.get("outliers") or []),
            }
        await self._sse_broker.publish(
            session_id,
            "pipeline_complete",
            {
                "status": result.get("status", "unknown"),
                "final_output_url": f"/api/runs/{session_id}/output",
                "judge_summary": judge_summary,
            },
        )

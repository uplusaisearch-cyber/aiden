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
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.agents.concrete_agents import build_all_agents
from backend.api.services.sse_broker import SSEBroker
from backend.llm.gemini_client import GeminiClient
from backend.orchestrators.full_pipeline import FullPipeline
from backend.orchestrators.trace_logger import TraceLogger
from backend.storage.outputs_store import upsert_output

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


def _extract_topic_title(run_dir: Path, fallback: str | None) -> str | None:
    """Strategy Planner 출력의 final_topic.title 우선, 없으면 fallback."""
    planner_path = run_dir / "agents" / "03_strategy_planner.json"
    if planner_path.exists():
        try:
            data = json.loads(planner_path.read_text(encoding="utf-8"))
            ft = ((data.get("output") or {}).get("final_topic") or {})
            title = ft.get("title")
            if title:
                return str(title)
        except (json.JSONDecodeError, OSError):
            pass
    return fallback


def _persist_output_record(
    *,
    session_id: str,
    category: str,
    custom_topic: str | None,
    target_category_label: str,
    result: dict[str, Any],
    cost_summary: dict | None,
    wrapped_final_html: str,
    tracer_run_dir: Path,
    tracer_started_at_iso: str,
) -> None:
    """run 결과 → outputs.db 적재용 record 조립 후 upsert.

    호출 조건은 호출자가 보장(정상 종료 + final_html). 본 함수 내부에서는 dict 조립만.
    upsert_output 자체가 예외를 삼키지만, 조립 단계 예외는 호출자의 try/except 가 catch.
    """
    title_fallback = custom_topic if category == "custom" else target_category_label
    topic_title = _extract_topic_title(tracer_run_dir, title_fallback)

    stage_4 = result.get("stage_4") or {}
    aggregate = stage_4.get("aggregate") or {}
    weighted_score = aggregate.get("weighted_total")
    scores = aggregate.get("mean_scores")

    total_tokens: int | None = None
    total_cost: float | None = None
    cost_is_estimated: bool | None = None
    if cost_summary:
        total = cost_summary.get("total") or {}
        total_tokens = total.get("total_tokens")
        total_cost = total.get("total_cost_usd")
        judge_part = cost_summary.get("judge") or {}
        # judge 비용이 추정이면 전체 합도 추정 포함으로 표기.
        cost_is_estimated = bool(
            judge_part and judge_part.get("is_actual_tokens") is False
        )

    record = {
        "run_id": session_id,
        "topic": topic_title,
        "category": category,
        "created_at": tracer_started_at_iso,
        "weighted_score": weighted_score,
        "scores_json": scores,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
        "cost_is_estimated": cost_is_estimated,
        "final_html": wrapped_final_html,
    }
    upsert_output(record)


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
        wrapped_final_html: str | None = None
        if final_html:
            wrapped_final_html = _apply_standalone_html_wrapper(
                target_category_label, final_html
            )
            try:
                final_path = tracer.run_dir / "final_output.html"
                final_path.write_text(wrapped_final_html, encoding="utf-8")
                logger.info("final_output.html 저장: %s", final_path)
            except OSError as e:
                logger.error("final_output.html 저장 실패: %s", e)

        # 비용/토큰 종속 저장 — 라이브 표시 X, run 결과물에만 박음.
        # newsroom(9 에이전트) 은 cost_tracker 의 실측 토큰, judge_panel 은 호출당 토큰 고정 추정.
        cost_summary: dict | None = None
        try:
            from backend.core.cost_tracker import get_cost_tracker
            from backend.orchestrators.judge_panel import (
                JUDGE_NAMES as _JUDGE_NAMES,
                _TOKEN_ESTIMATE as _JUDGE_TOK_EST,
            )

            snap = get_cost_tracker().snapshot(run_id=session_id)
            newsroom_prompt = int(snap.get("run_prompt_tokens", 0) or 0)
            newsroom_completion = int(snap.get("run_completion_tokens", 0) or 0)
            newsroom_total = newsroom_prompt + newsroom_completion
            newsroom_cost = float(snap.get("run_cost_usd", 0.0) or 0.0)

            stage_4_for_cost = result.get("stage_4") or {}
            judge_calls = len(_JUDGE_NAMES)
            judge_prompt = judge_calls * int(_JUDGE_TOK_EST["input"])
            judge_completion = judge_calls * int(_JUDGE_TOK_EST["output"])
            judge_total = judge_prompt + judge_completion
            judge_cost = float(stage_4_for_cost.get("cost_usd_estimate") or 0.0)

            cost_summary = {
                "newsroom": {
                    "prompt_tokens": newsroom_prompt,
                    "completion_tokens": newsroom_completion,
                    "total_tokens": newsroom_total,
                    "cost_usd": round(newsroom_cost, 6),
                    "is_actual_tokens": True,
                },
                "judge": {
                    "prompt_tokens": judge_prompt,
                    "completion_tokens": judge_completion,
                    "total_tokens": judge_total,
                    "cost_usd": round(judge_cost, 6),
                    "is_actual_tokens": False,
                    "note": (
                        "judge_panel._TOKEN_ESTIMATE 호출당 input=2000/output=1000 "
                        "고정 추정 — 실측 아님"
                    ),
                },
                "total": {
                    "total_tokens": newsroom_total + judge_total,
                    "total_cost_usd": round(newsroom_cost + judge_cost, 6),
                },
            }
        except Exception as e:  # noqa: BLE001 — cost 저장 실패가 run 종료를 막지 않게
            logger.warning("cost_summary 조립 실패: %s", e)

        # metadata 기록 + Stage 4 결과 병합 + 비용 종속 저장
        tracer.write_metadata(
            user_input={
                "category": category,
                "custom_topic": custom_topic,
                "skip_judge": skip_judge,
            },
            status=result.get("status", "unknown"),
            notes="B3-S3-B API 트리거",
            judge_panel=result.get("stage_4"),
            cost_summary=cost_summary,
        )

        # outputs.db 영속 적재 — 종료된 run 결과만, **정상 종료 + final_html 있을 때만**.
        # 실패 run / timeout / final_html 부재 케이스는 적재 skip(빈 HTML 레코드 방지).
        # 적재 실패가 SSE/응답을 깨지 않게 try/except + log 격리.
        run_status = result.get("status", "unknown")
        if run_status == "completed" and wrapped_final_html:
            try:
                _persist_output_record(
                    session_id=session_id,
                    category=category,
                    custom_topic=custom_topic,
                    target_category_label=target_category_label,
                    result=result,
                    cost_summary=cost_summary,
                    wrapped_final_html=wrapped_final_html,
                    tracer_run_dir=tracer.run_dir,
                    tracer_started_at_iso=tracer.started_at.isoformat(),
                )
            except Exception as e:  # noqa: BLE001 — 영속 실패가 run 응답을 깨지 않게
                logger.error("outputs.db 적재 호출 실패 sid=%s: %s", session_id, e)

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

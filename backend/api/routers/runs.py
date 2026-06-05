"""GET /api/runs, /api/runs/{id}, /api/runs/{id}/output — 실행 목록·상세·HTML."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from backend.api.schemas.run import RunDetail, RunListResponse, RunSummary, RunStageInfo
from backend.api.services.trace_converter import convert as convert_trace
from backend.api.utils.trace_loader import (
    list_run_sessions,
    load_final_html,
    load_run_detail,
    load_run_summary,
)

router = APIRouter(prefix="/api", tags=["runs"])


@router.get("/runs", response_model=RunListResponse)
def list_runs(
    limit: int = Query(10, ge=1, le=100),
    category: str | None = None,
    status: str | None = None,
) -> RunListResponse:
    """runs/ 폴더 스캔 후 최신 순으로 RunSummary 반환."""
    sessions = list_run_sessions()
    summaries: list[RunSummary] = []
    for sid in sessions:
        s = load_run_summary(sid)
        if s is None:
            continue
        if category and s.get("category") != category:
            continue
        if status and s.get("status") != status:
            continue
        summaries.append(RunSummary(**s))
    return RunListResponse(runs=summaries[:limit], total=len(summaries))


@router.get("/runs/{session_id}", response_model=RunDetail)
def get_run_detail(session_id: str) -> RunDetail:
    raw = load_run_detail(session_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"session_id={session_id} 없음")

    # raw_steps → ChatMessage 변환
    messages: list[dict] = []
    for step in raw["raw_steps"]:
        messages.extend(convert_trace(step))

    # stage 요약
    stages: list[RunStageInfo] = []
    # 매우 단순화: trace 기록상 stage 별 step 카운트
    by_stage: dict[int, dict] = {}
    for m in messages:
        s = m.get("stage", 0)
        by_stage.setdefault(s, {"count": 0, "iters": set()})
        by_stage[s]["count"] += 1
        it = m.get("iteration")
        if it is not None:
            by_stage[s]["iters"].add(it)
    for stage_num, info in sorted(by_stage.items()):
        stages.append(
            RunStageInfo(
                stage=stage_num,
                status="completed" if raw["status"] == "completed" else raw["status"],
                duration_ms=None,
                agents_completed=info["count"],
                iterations=len(info["iters"]) if info["iters"] else None,
            ),
        )

    # 2026-06-05: metadata["cost"] 를 명시 필드로 끌어올림 (과거 run 은 None).
    cost_section = (
        raw["metadata"].get("cost") if isinstance(raw.get("metadata"), dict) else None
    )

    # B4-S2 C2: metadata["planning_selection"] 의 user-facing 4필드만 노출.
    planning = (
        raw["metadata"].get("planning_selection")
        if isinstance(raw.get("metadata"), dict)
        else None
    )
    planning = planning if isinstance(planning, dict) else {}

    return RunDetail(
        session_id=raw["session_id"],
        category=raw["category"],
        status=raw["status"],
        started_at=raw["started_at"],
        ended_at=raw["ended_at"],
        duration_sec=raw["duration_sec"],
        messages=messages,
        stages=stages,
        judge_panel=raw["judge_panel"],
        final_output_html_url=(
            f"/api/runs/{session_id}/output" if raw["final_html_exists"] else None
        ),
        metadata=raw["metadata"],
        cost=cost_section,
        angle=planning.get("angle"),
        angle_label=planning.get("angle_label"),
        audience_segment=planning.get("audience_segment"),
        segment_label=planning.get("segment_label"),
    )


@router.get("/runs/{session_id}/output", response_class=HTMLResponse)
def get_run_output(session_id: str) -> HTMLResponse:
    html = load_final_html(session_id)
    if html is None:
        raise HTTPException(status_code=404, detail="final_output.html 없음")
    return HTMLResponse(content=html, status_code=200)

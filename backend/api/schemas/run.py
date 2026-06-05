"""GET /api/runs 응답 스키마."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class RunSummary(BaseModel):
    session_id: str
    category: str | None = None
    title: str | None = None
    status: str = "unknown"
    started_at: str | None = None
    duration_ms: int | None = None
    judge_weighted_total: float | None = None
    judge_status: str | None = None
    thumbnail_url: str | None = None


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    total: int


class RunStageInfo(BaseModel):
    stage: int
    status: str
    duration_ms: int | None = None
    agents_completed: int | None = None
    iterations: int | None = None


class RunDetail(BaseModel):
    session_id: str
    category: str | None = None
    status: str
    started_at: str | None = None
    ended_at: str | None = None
    duration_sec: int | None = None
    messages: list[dict[str, Any]] = []  # ChatMessage dict
    stages: list[RunStageInfo] = []
    judge_panel: dict[str, Any] | None = None
    final_output_html_url: str | None = None
    metadata: dict[str, Any] = {}
    # 2026-06-05: 토큰·비용 실측 종속 저장. metadata["cost"] 와 동일 dict 의 명시적 노출.
    # 구조: { newsroom: {tokens, cost, is_actual_tokens: True},
    #         judge: {tokens, cost, is_actual_tokens: False, note},
    #         total: {total_tokens, total_cost_usd} }
    # None = 과거 run (cost 섹션 미저장) 호환.
    cost: dict[str, Any] | None = None
    # B4-S2 C2: angle round-robin + segment rotate 결과.
    # 출처는 metadata["planning_selection"] 의 user-facing 4필드.
    # angle_directive / segment_persona 는 노출하지 않음 (LLM 주입용 — C3 에서 사용).
    # None = 과거 run (planning_selection 미저장) 또는 selector 실패 호환.
    angle: str | None = None
    angle_label: str | None = None
    audience_segment: str | None = None
    segment_label: str | None = None

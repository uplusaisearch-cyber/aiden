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

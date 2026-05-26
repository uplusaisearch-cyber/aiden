"""SSE / Trace 변환 결과 스키마."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Highlight(BaseModel):
    label: str
    value: str | float | int


class Badge(BaseModel):
    label: str
    value: str
    color: str | None = None  # success | warning | danger | info


class ChatMessage(BaseModel):
    id: str
    agent_id: str
    stage: int
    iteration: int | None = None
    timestamp: str | None = None
    duration_ms: int = 0
    headline: str = ""
    body_text: str = ""
    raw_json: dict[str, Any] = {}
    highlights: list[Highlight] = []
    badges: list[Badge] = []


class StageChangeEvent(BaseModel):
    stage: int
    stage_name: str
    previous_stage: int | None = None
    timestamp: str | None = None


class CostUpdateEvent(BaseModel):
    total_usd: float
    budget_usd: float
    elapsed_ms: int
    last_latency_ms: int | None = None


class JudgeEvalEvent(BaseModel):
    model: str
    overall_score: float
    scores: dict[str, int]
    one_line_verdict: str
    completed_count: int
    total_count: int = 3


class PipelineCompleteEvent(BaseModel):
    status: str
    final_output_url: str
    judge_summary: dict[str, Any] | None = None
    duration_ms: int | None = None
    total_cost_usd: float | None = None


class ErrorEvent(BaseModel):
    agent_id: str | None = None
    stage: int | None = None
    iteration: int | None = None
    error_message: str
    retry_count: int = 0
    is_recoverable: bool = False

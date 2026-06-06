"""POST /api/generate 요청/응답 스키마."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CategoryId = Literal["food", "ai-trend", "safety", "culture", "custom"]
SafetyMode = Literal["normal", "dry_run"]


class GenerateOptions(BaseModel):
    max_iter: int = Field(3, ge=1, le=3)
    skip_judge: bool = False
    safety_mode: SafetyMode = "normal"


class SelectionOverride(BaseModel):
    """B4-S2 후속: 사용자가 모달에서 명시 선택한 angle/segment.

    각 필드 None = "자동(회전)" — selector 가 round-robin 으로 채움.
    부분 override 도 지원 (한쪽만 명시, 다른쪽은 자동).
    빈 dict 또는 둘 다 None 이면 selection_override 자체를 None 으로 보낸 것과 동일.
    """
    angle: str | None = None
    audience_segment: str | None = None


class GenerateRequest(BaseModel):
    category: CategoryId
    custom_topic: str | None = None
    options: GenerateOptions = Field(default_factory=GenerateOptions)
    selection_override: SelectionOverride | None = None


class GenerateResponse(BaseModel):
    session_id: str
    status: Literal["started"] = "started"
    stream_url: str
    started_at: str

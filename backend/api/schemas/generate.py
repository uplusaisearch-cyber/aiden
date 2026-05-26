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


class GenerateRequest(BaseModel):
    category: CategoryId
    custom_topic: str | None = None
    options: GenerateOptions = Field(default_factory=GenerateOptions)


class GenerateResponse(BaseModel):
    session_id: str
    status: Literal["started"] = "started"
    stream_url: str
    started_at: str

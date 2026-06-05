"""Prompt CRUD 스키마."""
from __future__ import annotations

from pydantic import BaseModel


class PromptSummary(BaseModel):
    agent_id: str
    filename: str
    path: str
    size_bytes: int
    last_modified: str
    version_count: int = 0
    # B3-S3-E: 좌패널 표시 메타
    display_name: str | None = None
    emoji: str | None = None
    color_key: str | None = None


class PromptListResponse(BaseModel):
    prompts: list[PromptSummary]


class PromptDetail(BaseModel):
    agent_id: str
    content: str
    size_bytes: int
    last_modified: str
    detected_variables: list[str] = []
    estimated_tokens: int = 0


class PromptUpdate(BaseModel):
    content: str
    save_version: bool = True


class PromptUpdateResponse(BaseModel):
    agent_id: str
    saved_at: str
    size_bytes: int
    version_id: str | None = None
    diff_summary: str | None = None


class PromptHistoryEntry(BaseModel):
    timestamp: str            # 20260605T120000 (UTC, second-resolution)
    version_id: str           # "v3"
    filename: str             # "01_trend_scout_v3_20260605T120000.md"
    size_bytes: int


class PromptHistoryResponse(BaseModel):
    agent_id: str
    history: list[PromptHistoryEntry]


class PromptRollbackRequest(BaseModel):
    timestamp: str            # POST body — history entry timestamp


class PromptRestoreResponse(BaseModel):
    agent_id: str
    restored_from: str        # "defaults" | "history:<timestamp>"
    saved_at: str
    size_bytes: int

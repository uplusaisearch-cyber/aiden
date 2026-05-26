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

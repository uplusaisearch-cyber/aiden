"""Judge Panel 응답 스키마 — B3-S2 judge_panel.json 그대로 반환."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JudgePanelResponse(BaseModel):
    """raw judge_panel.json 을 그대로 dict 로 반환. 추가 가공 없음."""

    session_id: str
    judge: dict[str, Any]

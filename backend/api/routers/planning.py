"""GET /api/planning/presets — 프론트 모달이 angle/segment 선택지를 받아오는 read-only.

명세: B4-S2 후속 (사용자 명시 선택 모달).
- 단일 출처: backend/config/planning_presets.json
- selector 인스턴스의 ``list_presets()`` 를 그대로 노출. 캐시 X (파일 1회 로드는 selector __init__).
- 응답에 ``enabled`` 플래그 포함 — 프론트가 event_tie 같은 항목은 회색 처리/숨김 결정.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.services.planning_selector import PlanningSelector

router = APIRouter(prefix="/api/planning", tags=["planning"])


@router.get("/presets")
async def get_planning_presets() -> dict:
    try:
        return PlanningSelector.instance().list_presets()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"presets 로드 실패: {e}") from e

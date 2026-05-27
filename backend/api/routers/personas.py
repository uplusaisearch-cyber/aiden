"""GET /api/personas — 9 에이전트 페르소나 + 3 stage 메타 응답.

명세: docs/patches/2026-05-28_b3-s3-c_trace_viewer.md (§4)

프론트는 진입 시 1회 fetch 후 캐시. personas.yaml 변경은 서버 재시작 시 반영.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.api.services.humanizer import get_all_personas

router = APIRouter(prefix="/api/personas", tags=["personas"])


@router.get("")
def list_personas() -> dict:
    """전체 personas + stages 메타 반환."""
    return get_all_personas()

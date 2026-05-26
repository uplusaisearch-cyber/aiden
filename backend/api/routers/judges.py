"""GET /api/runs/{session_id}/judge — Judge Panel 결과 분리 응답."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas.judge import JudgePanelResponse
from backend.api.utils.trace_loader import RUNS_DIR, _safe_read_json, session_exists

router = APIRouter(prefix="/api", tags=["judges"])


@router.get("/runs/{session_id}/judge", response_model=JudgePanelResponse)
def get_judge(session_id: str) -> JudgePanelResponse:
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"session_id={session_id} 없음")
    jp = _safe_read_json(RUNS_DIR / session_id / "judge_panel.json")
    if jp is None:
        raise HTTPException(status_code=404, detail="judge_panel.json 없음")
    return JudgePanelResponse(session_id=session_id, judge=jp)

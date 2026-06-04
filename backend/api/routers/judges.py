"""GET /api/runs/{session_id}/judge — Judge Panel 시각화 응답.
   GET /api/runs/{session_id}/final-html — final_output.html 메타.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.api.schemas.judge import JudgeResult
from backend.api.services.judge_adapter import adapt_judge_panel
from backend.api.utils import trace_loader as tl

router = APIRouter(prefix="/api", tags=["judges"])


@router.get("/runs/{session_id}/judge", response_model=JudgeResult)
def get_judge(session_id: str) -> JudgeResult:
    if not tl.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"session_id={session_id} 없음")
    raw = tl._safe_read_json(tl.RUNS_DIR / session_id / "judge_panel.json")
    if raw is None:
        raise HTTPException(status_code=404, detail="judge_panel.json 없음")
    return adapt_judge_panel(raw, session_id)


@router.get("/runs/{session_id}/final-html")
def get_final_html_meta(session_id: str) -> dict:
    """iframe 미리보기용 메타. available=False 인 경우 url=None."""
    if not tl.session_exists(session_id):
        raise HTTPException(status_code=404, detail=f"session_id={session_id} 없음")
    final_path = tl.RUNS_DIR / session_id / "final_output.html"
    if not final_path.exists():
        return {"available": False, "url": None, "size_bytes": None}
    return {
        "available": True,
        "url": f"/api/runs/{session_id}/output",
        "size_bytes": final_path.stat().st_size,
    }

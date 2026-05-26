"""POST /api/generate — 콘텐츠 생성 시작."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_run_manager
from backend.api.schemas.generate import GenerateRequest, GenerateResponse
from backend.api.services.run_manager import RunManager

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=GenerateResponse, status_code=202)
async def start_generate(
    req: GenerateRequest,
    run_manager: RunManager = Depends(get_run_manager),
) -> GenerateResponse:
    """비동기 백그라운드로 FullPipeline 실행 시작, 즉시 session_id 반환."""
    if req.category == "custom" and not (req.custom_topic and req.custom_topic.strip()):
        raise HTTPException(
            status_code=422,
            detail="category=custom 일 때는 custom_topic 이 필요합니다.",
        )

    try:
        session_id = await run_manager.start_run(
            category=req.category,
            custom_topic=req.custom_topic,
            options=req.options.model_dump(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"start_run 실패: {e}") from e

    return GenerateResponse(
        session_id=session_id,
        status="started",
        stream_url=f"/api/stream/{session_id}",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

"""``/api/outputs`` — 영속 저장된 종료 run 결과 조회.

명세: docs/patches/2026-06-05_output-history-persistence.md

리스트 응답은 final_html 제외(페이로드 절감). 상세/다운로드는 final_html 포함.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from backend.storage.outputs_store import (
    count_outputs,
    get_output,
    list_outputs,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


class OutputSummary(BaseModel):
    run_id: str
    topic: str | None = None
    category: str | None = None
    created_at: str | None = None
    weighted_score: float | None = None
    scores: dict[str, Any] | None = None
    total_tokens: int | None = None
    total_cost_usd: float | None = None
    cost_is_estimated: bool | None = None


class OutputListResponse(BaseModel):
    outputs: list[OutputSummary]
    total: int


class OutputDetail(OutputSummary):
    final_html: str


@router.get("", response_model=OutputListResponse)
def list_outputs_endpoint(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> OutputListResponse:
    rows = list_outputs(limit=limit, offset=offset)
    return OutputListResponse(
        outputs=[OutputSummary(**r) for r in rows],
        total=count_outputs(),
    )


@router.get("/{run_id}", response_model=OutputDetail)
def get_output_endpoint(run_id: str) -> OutputDetail:
    row = get_output(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"run_id={run_id} 없음")
    return OutputDetail(**row)


_SAFE_FILENAME_RE = re.compile(r"[^0-9A-Za-z가-힣._-]+")


def _filename_for(row: dict[str, Any]) -> str:
    topic = (row.get("topic") or row.get("run_id") or "aiden-output").strip()
    safe = _SAFE_FILENAME_RE.sub("_", topic)[:80] or "aiden-output"
    return f"{safe}.html"


@router.get("/{run_id}/download")
def download_output(run_id: str) -> Response:
    row = get_output(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"run_id={run_id} 없음")
    filename = _filename_for(row)
    # RFC 6266 filename* 로 한글 파일명 안전 인코딩
    from urllib.parse import quote

    return Response(
        content=row["final_html"],
        media_type="text/html; charset=utf-8",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{quote(filename)}\"; "
                f"filename*=UTF-8''{quote(filename)}"
            ),
        },
    )

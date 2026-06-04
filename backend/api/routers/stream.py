"""GET /api/stream/{session_id} — SSE 스트리밍.

TraceLogger 가 publish 하는 raw payload 를 trace_converter 로 변환해
``event: chat`` 메시지로 전송. 다른 이벤트 (pipeline_start/complete, error) 는 그대로 forward.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.deps import get_run_manager, get_sse_broker
from backend.api.services.run_manager import RunManager
from backend.api.services.sse_broker import SSEBroker
from backend.api.services.trace_converter import convert as convert_trace
from backend.api.utils.trace_loader import session_exists

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["stream"])

# heartbeat ping 주기 (브라우저 idle timeout 방지)
HEARTBEAT_SEC = 30.0


def _sse_format(event: str, data: dict | None) -> str:
    payload = json.dumps(data or {}, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.get("/stream/{session_id}")
async def stream(
    session_id: str,
    broker: SSEBroker = Depends(get_sse_broker),
    run_manager: RunManager = Depends(get_run_manager),
) -> StreamingResponse:
    # 활성 run 또는 디스크에 존재하는 session 만 허용
    if (
        session_id not in run_manager.active_session_ids()
        and not session_exists(session_id)
    ):
        raise HTTPException(status_code=404, detail=f"session_id={session_id} 없음")

    async def gen() -> AsyncIterator[bytes]:
        # heartbeat 은 broker.subscribe 내부에서 처리한다. 외부에서 asyncio.wait_for 로
        # __anext__() 에 timeout 을 걸면 cancel 이 async generator 를 종료시켜 매 HEARTBEAT_SEC
        # 마다 stream 이 끊긴다 (B3-S3-C 라이브 SSE 30초 끊김 root cause).
        sub = broker.subscribe(session_id, heartbeat_sec=HEARTBEAT_SEC)
        yield _sse_format("ping", {"ts": "ready"}).encode("utf-8")
        events_sent = 0
        try:
            async for msg in sub:
                event = msg.get("event", "message")
                data = msg.get("data") or {}

                if event == "agent_step":
                    # raw trace → ChatMessage 변환
                    try:
                        chat_messages = convert_trace(data)
                        for cm in chat_messages:
                            yield _sse_format("chat", cm).encode("utf-8")
                            events_sent += 1
                    except Exception as e:  # noqa: BLE001
                        logger.warning("convert_trace 실패: %s", e)
                        yield _sse_format("error", {"error_message": str(e)}).encode("utf-8")
                else:
                    # 그 외 이벤트는 그대로 forward (heartbeat ping 포함)
                    yield _sse_format(event, data).encode("utf-8")
                    events_sent += 1
        finally:
            logger.info(
                "SSE stream closed session=%s events_sent=%d",
                session_id, events_sent,
            )
            try:
                await sub.aclose()
            except Exception:
                pass

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

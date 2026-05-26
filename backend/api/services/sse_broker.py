"""SSE pub/sub (asyncio.Queue 기반).

명세: docs/patches/2026-05-25_bundle3_step3_B_fastapi_sse_backend.md

publish 는 TraceLogger 가 별도 스레드에서 ``run_coroutine_threadsafe`` 로 main loop 에
스케줄 (TraceLogger._publish_sse_safe 참고). subscribe 는 FastAPI SSE 엔드포인트가 사용.

run_manager 는 publish 와 close 만 사용.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


_CLOSE_SENTINEL = "_close"


class SSEBroker:
    """단일 프로세스 내부의 pub/sub. 외부 메시지 브로커 (Redis 등) 미사용."""

    def __init__(self) -> None:
        # session_id -> [asyncio.Queue, ...]
        self._channels: dict[str, list[asyncio.Queue]] = {}

    async def publish(self, session_id: str, event: str, data: dict[str, Any]) -> None:
        """모든 구독자에게 이벤트 전달. 구독자 없으면 no-op."""
        queues = list(self._channels.get(session_id, []))
        if not queues:
            # 구독자 없을 때도 publish 호출은 정상 — 구독 시작 전 발생 가능
            return
        msg = {"event": event, "data": data}
        for queue in queues:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full for session=%s, event=%s — dropping",
                    session_id, event,
                )

    async def subscribe(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        """이 session 의 이벤트를 yield. close 이벤트 또는 generator close 시 종료."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._channels.setdefault(session_id, []).append(queue)
        try:
            while True:
                msg = await queue.get()
                if msg.get("event") == _CLOSE_SENTINEL:
                    return
                yield msg
        finally:
            try:
                self._channels[session_id].remove(queue)
            except (KeyError, ValueError):
                pass
            if not self._channels.get(session_id):
                self._channels.pop(session_id, None)

    async def close(self, session_id: str) -> None:
        """모든 구독자에게 close sentinel publish — subscribe 루프 종료."""
        await self.publish(session_id, _CLOSE_SENTINEL, {})

    def active_sessions(self) -> list[str]:
        return list(self._channels.keys())

    def subscriber_count(self, session_id: str) -> int:
        return len(self._channels.get(session_id, []))

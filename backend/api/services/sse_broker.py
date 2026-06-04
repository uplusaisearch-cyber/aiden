"""SSE pub/sub (asyncio.Queue 기반) + 채널별 message buffer / replay.

명세: docs/patches/2026-05-25_bundle3_step3_B_fastapi_sse_backend.md

publish 는 TraceLogger 가 별도 스레드에서 ``run_coroutine_threadsafe`` 로 main loop 에
스케줄 (TraceLogger._publish_sse_safe 참고). subscribe 는 FastAPI SSE 엔드포인트가 사용.

run_manager 는 publish 와 close 만 사용.

──────────────────────────────────────────────────────────────────────────
B3-S3-C 라이브 SSE 손실 fix (2026-06-01):
publish 시점에 구독자가 없으면 메시지가 silent drop 되던 문제 + EventSource
자동 재연결 사이의 publish 가 손실되는 문제를 채널별 ring buffer 로 해결.

- publish 마다 buffer 에 저장 (close sentinel 제외)
- subscribe 가 라이브 큐 추가 전 buffer 메시지를 우선 yield (replay)
- close 후 buffer 는 ``_BUFFER_TTL_SEC`` 동안 유지 → 재연결 클라이언트가 회수 가능
──────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, AsyncIterator

logger = logging.getLogger(__name__)


_CLOSE_SENTINEL = "_close"

# 채널당 최근 N 개 메시지 보관 (9 에이전트 + iter + judge ≈ 25 ~ 30, 여유 있게)
_BUFFER_MAX = 500

# close 후 buffer 유지 시간 (초). 이 시간 이후 첫 publish/subscribe 가 도달하면 정리.
_BUFFER_TTL_SEC = 30 * 60


class SSEBroker:
    """단일 프로세스 내부의 pub/sub. 외부 메시지 브로커 (Redis 등) 미사용.

    채널별로:
      - 활성 subscriber 큐 (broadcast 대상)
      - 최근 메시지 ring buffer (subscribe 시 replay)
    """

    def __init__(self) -> None:
        # session_id -> [asyncio.Queue, ...]
        self._channels: dict[str, list[asyncio.Queue]] = {}
        # session_id -> deque[message]
        self._buffers: dict[str, deque[dict[str, Any]]] = {}
        # session_id -> close 후 buffer expiry timestamp (epoch sec). None 이면 유효
        self._buffer_expires_at: dict[str, float] = {}

    async def publish(self, session_id: str, event: str, data: dict[str, Any]) -> None:
        """모든 구독자에게 이벤트 전달 + 버퍼 저장.

        구독자가 없어도 버퍼에는 저장됨 (재연결 / 늦은 subscribe 가 복구 가능).
        close sentinel 은 버퍼에 저장하지 않음 (replay 시 즉시 종료 방지).
        """
        msg = {"event": event, "data": data}

        if event != _CLOSE_SENTINEL:
            buf = self._buffers.setdefault(session_id, deque(maxlen=_BUFFER_MAX))
            buf.append(msg)
            # 만료 예약이 있었으면 publish 시점에 취소 (run 이 계속 진행 중)
            self._buffer_expires_at.pop(session_id, None)
            logger.debug(
                "SSE publish session=%s event=%s buffer_size=%d subscribers=%d",
                session_id, event, len(buf), len(self._channels.get(session_id, [])),
            )
        else:
            # close 호출 시점 — buffer expiry 예약
            self._buffer_expires_at[session_id] = time.time() + _BUFFER_TTL_SEC

        queues = list(self._channels.get(session_id, []))
        for queue in queues:
            try:
                queue.put_nowait(msg)
            except asyncio.QueueFull:
                logger.warning(
                    "SSE queue full for session=%s, event=%s — dropping",
                    session_id, event,
                )

    async def subscribe(
        self,
        session_id: str,
        heartbeat_sec: float | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """이 session 의 이벤트를 yield.

        흐름:
          1. 만료된 buffer 정리 (lazy GC, close 마커는 유지)
          2. snapshot 먼저 만들고 already_closed 면 buffer 만 yield 후 즉시 종료
          3. 그 외엔 라이브 큐 등록 후 snapshot replay → 라이브 메시지 yield
             (큐 등록은 snapshot 직후라 race window 0 — asyncio single-thread 보장)

        Args:
            session_id: SSE 채널 키.
            heartbeat_sec: 이 시간 동안 publish 가 없으면 ``{"event": "ping", "data": {}}``
                를 yield. ``None`` 이면 영구 대기. 외부에서 ``asyncio.wait_for(__anext__(), ...)``
                로 timeout 을 걸면 async generator 가 cancel 되어 종료되므로 (B3-S3-C 라이브
                SSE 30초 끊김의 root cause), heartbeat 는 반드시 generator 내부에서 처리한다.
        """
        self._gc_expired_buffer(session_id)

        already_closed = session_id in self._buffer_expires_at
        buffered_snapshot = list(self._buffers.get(session_id, ()))
        logger.info(
            "SSE subscribe session=%s replay=%d already_closed=%s heartbeat=%s",
            session_id, len(buffered_snapshot), already_closed, heartbeat_sec,
        )

        # already_closed: 새 publish 가 더 이상 오지 않으므로 buffer 만 회수하고 종료
        if already_closed:
            for msg in buffered_snapshot:
                yield msg
            return

        # 라이브 큐를 snapshot 직후 즉시 등록 (snapshot 이후의 publish 는 큐로만 들어가
        # buffer + 큐 중복 yield 가 발생하지 않음. asyncio single-thread 라 race 없음)
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._channels.setdefault(session_id, []).append(queue)

        try:
            # snapshot replay (이 시점의 buffer 내용. 이후 추가는 큐로 도착)
            for msg in buffered_snapshot:
                yield msg

            # 라이브: 큐에서 close sentinel 까지 대기. heartbeat 은 내부에서 처리.
            # wait_for 는 queue.get task 만 cancel 하므로 generator 는 살아있음.
            while True:
                if heartbeat_sec is None:
                    msg = await queue.get()
                else:
                    try:
                        msg = await asyncio.wait_for(queue.get(), timeout=heartbeat_sec)
                    except asyncio.TimeoutError:
                        yield {"event": "ping", "data": {}}
                        continue
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
        """모든 구독자에게 close sentinel publish — subscribe 루프 종료.

        buffer 는 ``_BUFFER_TTL_SEC`` 동안 유지 (재연결 클라이언트가 회수 가능).
        """
        logger.info("SSE close session=%s", session_id)
        await self.publish(session_id, _CLOSE_SENTINEL, {})

    def active_sessions(self) -> list[str]:
        return list(self._channels.keys())

    def subscriber_count(self, session_id: str) -> int:
        return len(self._channels.get(session_id, []))

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    def _gc_expired_buffer(self, session_id: str) -> None:
        """만료된 buffer 를 lazy GC. subscribe 진입 시 1회 호출.

        주의: close 마커 (``_buffer_expires_at`` 항목) 는 유지한다. 그래야 GC 이후에도
        subscribe 가 "이미 종료된 session" 으로 인식해 무한 대기하지 않음.
        """
        exp = self._buffer_expires_at.get(session_id)
        if exp is None:
            return
        if time.time() < exp:
            return
        # TTL 경과 → 메시지 buffer 만 정리 (close 마커는 유지)
        if session_id in self._buffers:
            self._buffers.pop(session_id, None)
            logger.info("SSE buffer expired & cleared for session=%s", session_id)

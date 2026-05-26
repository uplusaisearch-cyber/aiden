"""SSE 스트리밍 단위 테스트 (3건).

직접 SSE 응답 파싱 대신 broker pub/sub 동작 검증 + 404 케이스 검증.
완전한 SSE 통합은 통합 단계에서 별도 검증.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.services.sse_broker import SSEBroker


class TestSSEBroker:
    @pytest.mark.asyncio
    async def test_1_pub_sub_chat_event(self):
        """SSE broker: subscribe 후 publish 한 chat 이벤트 수신."""
        broker = SSEBroker()
        async def collect() -> list[dict]:
            out: list[dict] = []
            sub = broker.subscribe("s1")
            async for msg in sub:
                out.append(msg)
                if len(out) >= 1:
                    await broker.close("s1")
            return out

        async def emit() -> None:
            await asyncio.sleep(0.05)
            await broker.publish("s1", "chat", {"hello": "world"})

        results = await asyncio.gather(collect(), emit())
        msgs = results[0]
        assert len(msgs) == 1
        assert msgs[0]["event"] == "chat"
        assert msgs[0]["data"]["hello"] == "world"

    @pytest.mark.asyncio
    async def test_2_close_terminates_subscriber(self):
        """broker.close() 호출 시 subscribe 루프가 종료."""
        broker = SSEBroker()
        collected: list[dict] = []

        async def collect():
            async for msg in broker.subscribe("s2"):
                collected.append(msg)

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.05)
        await broker.close("s2")
        await asyncio.wait_for(task, timeout=1.0)
        assert collected == []  # close sentinel 만 보냈으니 yield 없음


class TestSSEEndpoint:
    def test_3_stream_404_for_unknown_session(self, tmp_path, monkeypatch):
        """존재하지 않는 session_id → 404."""
        from backend.api.utils import trace_loader as tl
        monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)

        with TestClient(create_app()) as client:
            r = client.get("/api/stream/nonexistent-id-xxxxxx")
        assert r.status_code == 404

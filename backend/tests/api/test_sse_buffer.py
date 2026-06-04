"""SSEBroker buffer / replay 동작 단위 테스트.

B3-S3-C 라이브 SSE 손실 fix (2026-06-01):
publish race 와 EventSource 재연결 시 메시지 손실을 broker buffer 로 방어.
"""
from __future__ import annotations

import asyncio
from collections import deque

import pytest

from backend.api.services import sse_broker as sse_mod
from backend.api.services.sse_broker import SSEBroker


@pytest.mark.asyncio
async def test_publish_before_subscribe_is_replayed():
    """구독자 없을 때 publish 된 메시지가 첫 subscribe 에 replay 되어야 한다."""
    broker = SSEBroker()
    # subscribe 전 3건 publish
    await broker.publish("s1", "pipeline_start", {"a": 1})
    await broker.publish("s1", "agent_step", {"a": 2})
    await broker.publish("s1", "agent_step", {"a": 3})

    collected: list[dict] = []

    async def collect():
        async for msg in broker.subscribe("s1"):
            collected.append(msg)
            if len(collected) >= 3:
                await broker.close("s1")

    await asyncio.wait_for(collect(), timeout=2.0)
    assert [m["event"] for m in collected] == ["pipeline_start", "agent_step", "agent_step"]
    assert [m["data"] for m in collected] == [{"a": 1}, {"a": 2}, {"a": 3}]


@pytest.mark.asyncio
async def test_reconnect_replays_all_history():
    """첫 연결이 끊긴 뒤 두 번째 연결도 동일하게 모든 history 를 replay 받아야 한다."""
    broker = SSEBroker()
    await broker.publish("s2", "pipeline_start", {"step": 1})
    await broker.publish("s2", "agent_step", {"step": 2})

    # 첫 subscribe — 1건만 받고 종료
    collected_first: list[dict] = []

    async def collect_first():
        async for msg in broker.subscribe("s2"):
            collected_first.append(msg)
            break  # 첫 메시지만 받고 즉시 종료 (EventSource 재연결 시뮬레이션)

    await asyncio.wait_for(collect_first(), timeout=2.0)
    assert len(collected_first) == 1

    # 추가 publish (재연결 사이)
    await broker.publish("s2", "agent_step", {"step": 3})

    # 두 번째 subscribe — buffer 의 모든 메시지를 replay 받아야 한다 (재연결 케이스)
    collected_second: list[dict] = []

    async def collect_second():
        async for msg in broker.subscribe("s2"):
            collected_second.append(msg)
            if len(collected_second) >= 3:
                await broker.close("s2")

    await asyncio.wait_for(collect_second(), timeout=2.0)
    steps = [m["data"]["step"] for m in collected_second]
    assert steps == [1, 2, 3]   # 첫 연결 중에 받은 1도 다시 replay


@pytest.mark.asyncio
async def test_live_messages_after_replay():
    """replay 직후 라이브로 publish 한 메시지도 정상 도달."""
    broker = SSEBroker()
    await broker.publish("s3", "pipeline_start", {"x": 1})

    collected: list[dict] = []

    async def collect():
        async for msg in broker.subscribe("s3"):
            collected.append(msg)
            if len(collected) >= 3:
                await broker.close("s3")

    async def emit():
        await asyncio.sleep(0.05)
        await broker.publish("s3", "agent_step", {"x": 2})
        await broker.publish("s3", "pipeline_complete", {"x": 3})

    await asyncio.wait_for(asyncio.gather(collect(), emit()), timeout=2.0)
    xs = [m["data"]["x"] for m in collected]
    assert xs == [1, 2, 3]


@pytest.mark.asyncio
async def test_close_sentinel_not_buffered():
    """close sentinel 은 buffer 에 저장되지 않아야 한다 (재연결 시 즉시 종료 방지)."""
    broker = SSEBroker()
    await broker.publish("s4", "agent_step", {"v": 1})
    await broker.close("s4")

    # buffer 에는 sentinel 없이 agent_step 만
    buf = list(broker._buffers.get("s4", deque()))
    assert len(buf) == 1
    assert buf[0]["event"] == "agent_step"


@pytest.mark.asyncio
async def test_subscribe_after_close_returns_buffer_then_ends():
    """close 후 subscribe 는 buffer 를 한 번에 replay 한 뒤 즉시 종료한다."""
    broker = SSEBroker()
    await broker.publish("s5", "pipeline_start", {"k": "a"})
    await broker.publish("s5", "agent_step", {"k": "b"})
    await broker.publish("s5", "pipeline_complete", {"k": "c"})
    await broker.close("s5")

    collected: list[dict] = []

    async def collect():
        async for msg in broker.subscribe("s5"):
            collected.append(msg)

    # close 후이므로 즉시 종료 (timeout 안 걸려야 함)
    await asyncio.wait_for(collect(), timeout=2.0)
    ks = [m["data"]["k"] for m in collected]
    assert ks == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_buffer_ttl_gc(monkeypatch):
    """close 후 TTL 경과 시 다음 subscribe 가 buffer 를 GC 한다."""
    broker = SSEBroker()
    await broker.publish("s6", "agent_step", {"v": 1})
    await broker.close("s6")
    assert "s6" in broker._buffers

    # 시간을 TTL 너머로 점프
    monkeypatch.setattr(sse_mod, "_BUFFER_TTL_SEC", -1)
    broker._buffer_expires_at["s6"] = 0.0  # 이미 만료

    # 다음 subscribe 가 GC 실행
    async def collect():
        async for _ in broker.subscribe("s6"):
            pass

    await asyncio.wait_for(collect(), timeout=2.0)
    assert "s6" not in broker._buffers

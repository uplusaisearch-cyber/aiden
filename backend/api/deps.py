"""FastAPI 공통 의존성 — SSEBroker / RunManager 싱글톤 제공.

lifespan 내부에서 인스턴스화하고 ``app.state`` 에 보관.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Request

from backend.api.services.run_manager import RunManager
from backend.api.services.sse_broker import SSEBroker


def get_sse_broker(request: Request) -> SSEBroker:
    return request.app.state.sse_broker


def get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


def get_uptime_sec(request: Request) -> int:
    started: datetime = request.app.state.started_at
    return int((datetime.now(timezone.utc) - started).total_seconds())

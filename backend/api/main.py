"""FastAPI 앱 진입점.

명세: docs/patches/2026-05-25_bundle3_step3_B_fastapi_sse_backend.md

기동:
    uvicorn backend.api.main:app --reload --port 8000
또는:
    python scripts/run_api_server.py
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.deps import get_run_manager, get_sse_broker, get_uptime_sec
from backend.api.routers import generate, judges, personas, prompts, runs, stream
from backend.api.services.run_manager import RunManager
from backend.api.services.sse_broker import SSEBroker

logger = logging.getLogger(__name__)


def _cors_origins() -> list[str]:
    raw = os.getenv("API_CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 lifecycle. SSEBroker + RunManager 싱글톤 초기화."""
    broker = SSEBroker()
    run_manager = RunManager(sse_broker=broker)
    app.state.sse_broker = broker
    app.state.run_manager = run_manager
    app.state.started_at = datetime.now(timezone.utc)
    logger.info("AIDEN API 서버 기동 (CORS=%s)", _cors_origins())
    yield
    # 종료 시 정리 (실행 중 task 를 강제 종료하지는 않음 — to_thread 가동 중일 수 있음)
    logger.info("AIDEN API 서버 종료")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AIDEN API",
        version="0.1.0",
        description="9 AI 에이전트 + 3 Judge 뉴스룸 백엔드 (B3-S3-B)",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(generate.router)
    app.include_router(runs.router)
    app.include_router(stream.router)
    app.include_router(prompts.router)
    app.include_router(judges.router)
    app.include_router(personas.router)

    @app.get("/api/health", tags=["health"])
    async def health(
        uptime_sec: int = Depends(get_uptime_sec),
        run_manager: RunManager = Depends(get_run_manager),
        broker: SSEBroker = Depends(get_sse_broker),
    ):
        judge_available = False
        try:
            from backend.orchestrators.judge_panel import JudgePanel
            JudgePanel.from_settings()
            judge_available = True
        except Exception:
            judge_available = False
        return {
            "status": "ok",
            "version": "0.1.0",
            "uptime_sec": uptime_sec,
            "active_runs": run_manager.active_count(),
            "subscribers": sum(broker.subscriber_count(s) for s in broker.active_sessions()),
            "judge_panel_available": judge_available,
        }

    return app


app = create_app()

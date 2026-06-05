"""RunManager runs_base_dir 절대경로 default 검증.

회귀 방어: dev 가 ``backend/`` 서브폴더에서 uvicorn 띄웠을 때
저장 cwd 종속 → API 읽기 절대경로(`trace_loader.RUNS_DIR`) 불일치 →
GET /api/runs/* 404 유발하던 잠복 버그 fix.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from backend.api.services.run_manager import RunManager
from backend.api.utils.trace_loader import RUNS_DIR
from backend.core.settings import PROJECT_ROOT


def test_default_runs_base_dir_is_absolute_and_matches_loader():
    """인자 없이 생성 시 절대경로 + trace_loader.RUNS_DIR 와 동일 위치."""
    rm = RunManager(sse_broker=MagicMock())
    base = Path(rm._runs_base_dir)
    assert base.is_absolute(), f"기본 base_dir 가 상대경로: {rm._runs_base_dir!r}"
    assert base == PROJECT_ROOT / "runs"
    # trace_loader 읽기 경로와 정확히 일치해야 GET 404 안 남.
    assert base == RUNS_DIR


def test_custom_runs_base_dir_respected(tmp_path):
    """명시 인자는 그대로 사용 (테스트 격리·임시 경로 지원)."""
    rm = RunManager(sse_broker=MagicMock(), runs_base_dir=tmp_path)
    assert rm._runs_base_dir == str(tmp_path)


def test_custom_runs_base_dir_string_form():
    """str 인자도 그대로 사용."""
    rm = RunManager(sse_broker=MagicMock(), runs_base_dir="custom_runs")
    assert rm._runs_base_dir == "custom_runs"

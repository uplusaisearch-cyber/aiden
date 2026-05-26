"""GET /api/runs 단위 테스트 (4건)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app


def _make_run_dir(base: Path, session_id: str, category: str, status: str,
                  judge_weighted: float | None = None, title: str | None = None) -> Path:
    rd = base / session_id
    (rd / "agents").mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": session_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "duration_sec": 300,
        "user_input": {"category": category},
        "status": status,
        "step_count": 9,
        "notes": "test",
    }
    if judge_weighted is not None:
        metadata["judge_panel"] = {
            "status": "completed",
            "weighted_total": judge_weighted,
            "models_used": {"gemini": "gemini-2.5-pro", "gpt": "gpt-5", "claude": "claude-opus-4-7"},
        }
    (rd / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    if title:
        planner = {"output": {"final_topic": {"title": title}}}
        (rd / "agents" / "03_strategy_planner.json").write_text(
            json.dumps(planner, ensure_ascii=False), encoding="utf-8",
        )
    return rd


@pytest.fixture
def client_with_runs(tmp_path, monkeypatch):
    # trace_loader.RUNS_DIR 를 tmp_path 로 monkeypatch
    from backend.api.utils import trace_loader as tl
    monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)

    _make_run_dir(tmp_path, "2026-05-26T14-00-00_aaaaaaaa", "food", "completed", 73.4, "맛집 A")
    _make_run_dir(tmp_path, "2026-05-26T15-00-00_bbbbbbbb", "safety", "partial", 56.5, "안전 B")
    _make_run_dir(tmp_path, "2026-05-26T16-00-00_cccccccc", "food", "failed", None, "맛집 C")

    return TestClient(create_app())


class TestRuns:
    def test_1_list_runs(self, client_with_runs):
        r = client_with_runs.get("/api/runs")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["runs"]) == 3
        # 최신순 정렬 확인
        assert body["runs"][0]["session_id"].startswith("2026-05-26T16")

    def test_2_filter_by_category(self, client_with_runs):
        r = client_with_runs.get("/api/runs?category=food")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert all(run["category"] == "food" for run in body["runs"])

    def test_3_judge_weighted_total(self, client_with_runs):
        r = client_with_runs.get("/api/runs")
        body = r.json()
        food_completed = next(
            run for run in body["runs"]
            if run["category"] == "food" and run["status"] == "completed"
        )
        assert food_completed["judge_weighted_total"] == 73.4

    def test_4_empty_runs(self, tmp_path, monkeypatch):
        from backend.api.utils import trace_loader as tl
        monkeypatch.setattr(tl, "RUNS_DIR", tmp_path)
        client = TestClient(create_app())
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert r.json() == {"runs": [], "total": 0}

"""POST /api/generate 단위 테스트 (2건).

run_manager 를 monkeypatch 해서 실제 LLM 호출 없이 검증.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.services.run_manager import RunManager


class TestGenerate:
    def test_1_post_returns_session_id(self, monkeypatch):
        """POST → 즉시 session_id 응답 + 백그라운드 task 생성."""
        recorded: dict = {}

        async def fake_start_run(self, *, category, custom_topic, options, session_id=None):
            recorded["category"] = category
            recorded["options"] = options
            return "test-session-1234"

        monkeypatch.setattr(RunManager, "start_run", fake_start_run)

        # TestClient context manager 로 lifespan 실행
        with TestClient(create_app()) as client:
            r = client.post(
                "/api/generate",
                json={"category": "food", "options": {"max_iter": 3, "skip_judge": True}},
            )
        assert r.status_code == 202
        body = r.json()
        assert body["session_id"] == "test-session-1234"
        assert body["status"] == "started"
        assert body["stream_url"].endswith("test-session-1234")
        assert recorded["category"] == "food"
        assert recorded["options"]["skip_judge"] is True

    def test_2_invalid_category_returns_422(self):
        """category 가 enum 밖이면 422."""
        with TestClient(create_app()) as client:
            r = client.post(
                "/api/generate",
                json={"category": "INVALID_CATEGORY", "options": {}},
            )
        assert r.status_code == 422

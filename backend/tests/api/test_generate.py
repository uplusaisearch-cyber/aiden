"""POST /api/generate 단위 테스트.

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

        async def fake_start_run(self, **kwargs):
            recorded.update(kwargs)
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
        # selection_override 미지정 시 None 으로 전달돼야 함 (기존 흐름 보존)
        assert recorded["selection_override"] is None

    def test_2_invalid_category_returns_422(self):
        """category 가 enum 밖이면 422."""
        with TestClient(create_app()) as client:
            r = client.post(
                "/api/generate",
                json={"category": "INVALID_CATEGORY", "options": {}},
            )
        assert r.status_code == 422

    def test_3_selection_override_passes_through(self, monkeypatch):
        """selection_override 가 body 로 들어오면 RunManager.start_run 까지 dict 로 전달."""
        recorded: dict = {}

        async def fake_start_run(self, **kwargs):
            recorded.update(kwargs)
            return "sid-override-1"

        monkeypatch.setattr(RunManager, "start_run", fake_start_run)

        with TestClient(create_app()) as client:
            r = client.post(
                "/api/generate",
                json={
                    "category": "food",
                    "options": {"skip_judge": True},
                    "selection_override": {
                        "angle": "contrast",
                        "audience_segment": "twenties_newbie",
                    },
                },
            )
        assert r.status_code == 202
        assert recorded["selection_override"] == {
            "angle": "contrast",
            "audience_segment": "twenties_newbie",
        }

    def test_4_selection_override_partial_only_angle(self, monkeypatch):
        """angle 만 명시, segment 는 None — selector 가 segment 만 자동 회전 분기 발동."""
        recorded: dict = {}

        async def fake_start_run(self, **kwargs):
            recorded.update(kwargs)
            return "sid-partial-1"

        monkeypatch.setattr(RunManager, "start_run", fake_start_run)

        with TestClient(create_app()) as client:
            r = client.post(
                "/api/generate",
                json={
                    "category": "food",
                    "options": {},
                    "selection_override": {"angle": "ranking"},
                },
            )
        assert r.status_code == 202
        assert recorded["selection_override"] == {
            "angle": "ranking",
            "audience_segment": None,
        }

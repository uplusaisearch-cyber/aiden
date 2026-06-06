"""GET /api/planning/presets 단위 테스트.

명세: B4-S2 후속 — 프론트 모달이 angle/segment 선택지를 받아오는 read-only.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.services.planning_selector import PlanningSelector


class TestPlanningPresetsEndpoint:
    def test_1_returns_9_angles_and_7_segments(self):
        """presets.json 그대로 노출 (9 angles + 7 segments)."""
        PlanningSelector.reset_instance()
        with TestClient(create_app()) as client:
            r = client.get("/api/planning/presets")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"angles", "segments"}
        assert len(body["angles"]) == 9
        assert len(body["segments"]) == 7

    def test_2_event_tie_marked_disabled(self):
        """event_tie 만 enabled=false, 나머지 8개는 true."""
        PlanningSelector.reset_instance()
        with TestClient(create_app()) as client:
            r = client.get("/api/planning/presets")
        body = r.json()
        evt = next(a for a in body["angles"] if a["key"] == "event_tie")
        assert evt["enabled"] is False
        enabled_count = sum(1 for a in body["angles"] if a["enabled"])
        assert enabled_count == 8

    def test_3_segment_has_persona_field(self):
        """각 segment 에 persona 문자열 포함."""
        PlanningSelector.reset_instance()
        with TestClient(create_app()) as client:
            r = client.get("/api/planning/presets")
        body = r.json()
        for s in body["segments"]:
            assert set(s.keys()) == {"key", "label", "persona"}
            assert isinstance(s["persona"], str) and s["persona"]

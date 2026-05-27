"""GET /api/personas API 테스트 (4건).

명세: docs/patches/2026-05-28_b3-s3-c_trace_viewer.md §11-2.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app
from backend.api.services import humanizer
from backend.api.services.humanizer import load_personas


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.fixture(autouse=True)
def _reset_persona_cache():
    load_personas.cache_clear()
    humanizer._alias_map.cache_clear()
    yield
    load_personas.cache_clear()
    humanizer._alias_map.cache_clear()


class TestPersonasAPI:
    def test_1_get_personas_returns_200(self, client):
        res = client.get("/api/personas")
        assert res.status_code == 200
        data = res.json()
        assert "personas" in data and "stages" in data

    def test_2_all_9_agents_present(self, client):
        data = client.get("/api/personas").json()
        expected = {
            "scout", "analyst", "planner", "writer", "factchecker",
            "devils", "editor", "architect", "builder",
        }
        assert set(data["personas"].keys()) == expected

    def test_3_each_persona_has_required_fields(self, client):
        data = client.get("/api/personas").json()
        required = {"display_name", "emoji", "stage", "color_hex", "speech"}
        for key, p in data["personas"].items():
            missing = required - set(p.keys())
            assert not missing, f"{key} 에 필수 필드 누락: {missing}"
            sp = p["speech"]
            assert "prefix_options" in sp and "suffix_options" in sp
            assert isinstance(sp["prefix_options"], list)
            assert isinstance(sp["suffix_options"], list)

    def test_4_cache_clear_reflects_persona_change(self, client, tmp_path, monkeypatch):
        """personas.yaml 변경 → cache_clear → API 반영."""
        # 일단 한 번 호출 → 캐시 채우기
        before = client.get("/api/personas").json()
        original_emoji = before["personas"]["scout"]["emoji"]

        # 임시 personas.yaml 로 _PERSONAS_PATH monkeypatch
        custom = tmp_path / "personas.yaml"
        custom.write_text(
            """
version: 1
personas:
  scout:
    display_name: "변경됨"
    nickname: "x"
    emoji: "🚀"
    oneliner: "x"
    stage: "topic_newsroom"
    order: 1
    color_hex: "#000000"
    aliases: []
    speech:
      prefix_options: ["x"]
      suffix_options: ["x"]
      filler_options: []
stages:
  topic_newsroom:
    display_name: "x"
    subtitle: "x"
    emoji: "x"
    stage_no: 1
    agents: ["scout"]
""",
            encoding="utf-8",
        )
        monkeypatch.setattr(humanizer, "_PERSONAS_PATH", custom)
        load_personas.cache_clear()
        humanizer._alias_map.cache_clear()

        after = client.get("/api/personas").json()
        assert after["personas"]["scout"]["emoji"] == "🚀"
        assert after["personas"]["scout"]["emoji"] != original_emoji

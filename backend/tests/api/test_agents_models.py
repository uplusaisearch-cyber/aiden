"""GET /api/agents/models 단위 테스트.

B4-S1 모델 라우팅 결과를 프론트에 노출하는 endpoint 검증.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app


def _get(client: TestClient) -> dict:
    res = client.get("/api/agents/models")
    assert res.status_code == 200, res.text
    return res.json()


def test_endpoint_returns_newsroom_and_judges():
    with TestClient(app) as c:
        data = _get(c)
    assert "newsroom" in data
    assert "judges" in data


def test_newsroom_short_keys_present():
    """9개 short_key 모두 노출되며 ChatMessage.agent_id 와 일치."""
    expected = {
        "scout", "analyst", "planner",
        "writer", "factchecker", "devils", "editor",
        "architect", "builder",
    }
    with TestClient(app) as c:
        data = _get(c)
    assert set(data["newsroom"].keys()) == expected


def test_planner_uses_pro_hi():
    """B4-S1: planner 는 gemini-3.1-pro-preview 유지.

    B4-S2(Writer/Editor Claude 전환) 이후 pro_hi 사용 에이전트는 planner 1종만 남음.
    """
    with TestClient(app) as c:
        data = _get(c)
    entry = data["newsroom"]["planner"]
    assert entry["alias"] == "gemini_pro_hi", entry
    assert entry["model_id"] == "gemini-3.1-pro-preview", entry


def test_writer_editor_use_anthropic():
    """B4-S2: Writer → claude-sonnet-4-6, Editor → claude-opus-4-7."""
    with TestClient(app) as c:
        data = _get(c)
    writer = data["newsroom"]["writer"]
    assert writer["alias"] == "anthropic_sonnet", writer
    assert writer["model_id"] == "claude-sonnet-4-6", writer
    editor = data["newsroom"]["editor"]
    assert editor["alias"] == "anthropic_opus", editor
    assert editor["model_id"] == "claude-opus-4-7", editor


def test_pro_agents_use_2_5_pro():
    """architect/builder 는 GA 2.5-pro."""
    with TestClient(app) as c:
        data = _get(c)
    for key in ("architect", "builder"):
        assert data["newsroom"][key]["model_id"] == "gemini-2.5-pro"


def test_flash_agents_unchanged():
    """scout/analyst/factchecker/devils 는 현행 2.5-flash 유지."""
    with TestClient(app) as c:
        data = _get(c)
    for key in ("scout", "analyst", "factchecker", "devils"):
        assert data["newsroom"][key]["model_id"] == "gemini-2.5-flash"


def test_grounding_flags():
    """grounding 매핑은 scout/factchecker 만 True (B4-S1 회귀: 기존 정책 유지)."""
    with TestClient(app) as c:
        data = _get(c)
    assert data["newsroom"]["scout"]["grounding"] is True
    assert data["newsroom"]["factchecker"]["grounding"] is True
    assert data["newsroom"]["analyst"]["grounding"] is False
    assert data["newsroom"]["planner"]["grounding"] is False


def test_judges_present():
    """Judge Panel 3종 모델 매핑 노출."""
    with TestClient(app) as c:
        data = _get(c)
    judges = data["judges"]
    assert set(judges.keys()) >= {"gemini", "gpt", "claude"}
    assert judges["gemini"]
    assert judges["gpt"]
    assert judges["claude"]

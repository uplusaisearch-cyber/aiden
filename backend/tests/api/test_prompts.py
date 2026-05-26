"""Prompts CRUD 단위 테스트 (3건)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


class TestPrompts:
    def test_1_list_12_agents(self, client):
        """12 에이전트 prompt 목록 응답."""
        r = client.get("/api/prompts")
        assert r.status_code == 200
        prompts = r.json()["prompts"]
        agent_ids = {p["agent_id"] for p in prompts}
        # 9 newsroom + 3 judge = 12
        assert len(agent_ids) == 12
        assert "scout" in agent_ids
        assert "judge-gemini" in agent_ids
        # size_bytes > 0
        for p in prompts:
            assert p["size_bytes"] > 0

    def test_2_get_single_prompt_detail(self, client):
        """단일 prompt 내용 + detected_variables 추출."""
        r = client.get("/api/prompts/scout")
        assert r.status_code == 200
        body = r.json()
        assert body["agent_id"] == "scout"
        assert len(body["content"]) > 100
        assert body["estimated_tokens"] > 0
        assert isinstance(body["detected_variables"], list)

    def test_3_put_creates_backup(self, client, tmp_path, monkeypatch):
        """PUT 으로 수정 → 백업 파일 생성 확인."""
        # 실제 파일 수정 대신 임시 디렉토리로 redirect
        from backend.api.routers import prompts as prompts_mod

        # 실제 prompts/ 폴더에 영향을 안 주려면 모듈의 PROMPTS_DIR 자체를 교체
        # 그러나 router 가 모듈 글로벌을 사용하므로 monkeypatch 로 교체
        fake_prompts = tmp_path / "prompts"
        fake_versions = fake_prompts / ".versions"
        fake_prompts.mkdir(parents=True, exist_ok=True)
        target = fake_prompts / "01_trend_scout.md"
        target.write_text("# Trend Scout v0\n\nOriginal content.", encoding="utf-8")

        monkeypatch.setattr(prompts_mod, "PROMPTS_DIR", fake_prompts)
        monkeypatch.setattr(prompts_mod, "VERSIONS_DIR", fake_versions)

        r = client.put(
            "/api/prompts/scout",
            json={"content": "# Trend Scout v1\n\nNew content here.", "save_version": True},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["agent_id"] == "scout"
        assert body["version_id"] is not None
        # 백업 파일 존재
        backups = list(fake_versions.glob("01_trend_scout_v*.md"))
        assert len(backups) == 1
        # 새 내용 저장됨
        assert "New content here" in target.read_text(encoding="utf-8")

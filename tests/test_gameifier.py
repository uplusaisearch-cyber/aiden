"""Game-ifier 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable 로 흐름 검증.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.orchestrators.gameifier import Gameifier
from backend.orchestrators.trace_logger import TraceLogger


@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


@pytest.fixture
def final_content() -> dict:
    return {
        "category": "맛집",
        "title": "테스트 제목",
        "subtitle": "테스트 부제",
        "intro": "도입",
        "sections": [
            {"heading": "s1", "body": "본문 1 [출처: naver.com, 2026-05]"},
            {"heading": "s2", "body": "본문 2"},
        ],
        "closing": "마무리",
        "cta": "CTA",
        "sources": [{"domain": "naver.com", "url": "https://...", "date": "2026-05"}],
        "known_weaknesses": [],
    }


def _fa_a_type(_input: dict) -> dict:
    return {
        "format_analysis": "단순 정보 콘텐츠",
        "selected_type": "A",
        "base_layout": "A",
        "type_reasoning": "정보 전달 위주, 인터랙티브 가치 없음",
        "layout_hints": {
            "hero_image_needed": True,
            "image_count": 2,
            "image_descriptions": ["히어로 이미지", "섹션 이미지"],
        },
        "placeholder_locations": [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ],
    }


def _hb_ok(_input: dict) -> dict:
    return {
        "html": "<article><h1>테스트 제목</h1><section>...</section></article>",
        "selected_type_applied": "A",
        "base_layout_used": "A",
        "interactive_template_used": None,
        "placeholder_substitutions": [],
        "preserved_placeholders": ["{{HERO_IMAGE_URL}}"],
        "warnings": [],
    }


class TestGameifierHappyPath:

    def test_a_type_no_interactive(self, tracer: TraceLogger, final_content: dict) -> None:
        gi = Gameifier(tracer, _fa_a_type, _hb_ok)
        result = gi.run(final_content=final_content)

        assert "html" in result
        assert result["format_decision"]["selected_type"] == "A"
        assert "html_meta" in result

    def test_trace_files_created(self, tracer: TraceLogger, final_content: dict) -> None:
        gi = Gameifier(tracer, _fa_a_type, _hb_ok)
        gi.run(final_content=final_content)

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("08_format_architect" in f for f in files)
        assert any("09_html_builder" in f for f in files)


class TestGameifierFallback:

    def test_fa_fail_uses_fallback(self, tracer: TraceLogger, final_content: dict) -> None:
        def _fa_fail(_input: dict) -> dict:
            return {}  # selected_type 없음

        gi = Gameifier(tracer, _fa_fail, _hb_ok)
        result = gi.run(final_content=final_content)

        assert "html" in result
        assert result["error"].startswith("format_architect_failed")
        assert result["html_meta"]["_orchestrator_fallback"] is True
        # fallback HTML 에 타이틀이 들어가야 함
        assert "테스트 제목" in result["html"]

    def test_hb_fail_uses_fallback(self, tracer: TraceLogger, final_content: dict) -> None:
        def _hb_fail(_input: dict) -> dict:
            return {"html": ""}  # html 비어있음

        gi = Gameifier(tracer, _fa_a_type, _hb_fail)
        result = gi.run(final_content=final_content)

        assert "html" in result
        assert result["error"].startswith("html_builder_failed")
        assert "테스트 제목" in result["html"]

    def test_fa_raises_exception_fallback(
        self, tracer: TraceLogger, final_content: dict
    ) -> None:
        def _fa_raise(_input: dict) -> dict:
            raise RuntimeError("FA down")

        gi = Gameifier(tracer, _fa_raise, _hb_ok)
        result = gi.run(final_content=final_content)

        assert result["html_meta"]["_orchestrator_fallback"] is True


class TestGameifierBaseOrder:

    def test_custom_base_order(self, tracer: TraceLogger, final_content: dict) -> None:
        """base_order=8이 아닌 다른 값 사용 시 파일명 변경."""
        gi = Gameifier(tracer, _fa_a_type, _hb_ok, base_order=10)
        gi.run(final_content=final_content)

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("10_format_architect" in f for f in files)
        assert any("11_html_builder" in f for f in files)

"""base_agent.py 단위 테스트.

실제 LLM 호출 없음. placeholder 주입(`PromptLoader`) + 화이트리스트
치환(`WhitelistedSubstitutor`) 로직만 검증.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.core.base_agent import PromptLoader, WhitelistedSubstitutor


# =====================================================================
# 헬퍼
# =====================================================================
def _write_resources_config(
    tmp_path: Path,
    entries: dict[str, dict],
) -> Path:
    """tmp_path 에 agent_resources.json 작성 후 경로 반환."""
    config_path = tmp_path / "agent_resources.json"
    config_path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return config_path


def _write_prompt(tmp_path: Path, filename: str, content: str) -> Path:
    """tmp_path/prompts/ 에 prompt 파일 작성."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(exist_ok=True)
    fp = prompts_dir / filename
    fp.write_text(content, encoding="utf-8")
    return fp


# =====================================================================
# PromptLoader 테스트
# =====================================================================
class TestPromptLoader:

    def test_load_simple_prompt(self, tmp_path: Path) -> None:
        """placeholder 없는 prompt 는 그대로 반환."""
        _write_prompt(tmp_path, "test.md", "# Hello\n본문입니다.")
        config_path = _write_resources_config(tmp_path, {})

        loader = PromptLoader(
            prompts_dir=tmp_path / "prompts",
            resources_config_path=config_path,
        )
        result = loader.load("test.md")
        assert result == "# Hello\n본문입니다."

    def test_substitute_tone_reference(self, tmp_path: Path) -> None:
        """``{{TONE_REFERENCE}}`` placeholder 가 file 내용으로 치환된다."""
        tone_file = tmp_path / "tone.md"
        tone_file.write_text("톤 가이드: 정중하게.", encoding="utf-8")

        _write_prompt(
            tmp_path,
            "writer.md",
            "# Writer\n\n## 톤\n{{TONE_REFERENCE}}\n",
        )
        config_path = _write_resources_config(
            tmp_path,
            {
                "TONE_REFERENCE": {
                    "source_type": "file",
                    "path": str(tone_file),
                }
            },
        )

        loader = PromptLoader(
            prompts_dir=tmp_path / "prompts",
            resources_config_path=config_path,
        )
        result = loader.load("writer.md")
        assert "톤 가이드: 정중하게." in result
        assert "{{TONE_REFERENCE}}" not in result

    def test_undefined_placeholder_preserved(self, tmp_path: Path) -> None:
        """resource_map 에 없는 ``{{UNKNOWN_VAR}}`` 은 그대로 보존된다."""
        _write_prompt(tmp_path, "test.md", "값: {{UNKNOWN_VAR}}")
        config_path = _write_resources_config(tmp_path, {})

        loader = PromptLoader(
            prompts_dir=tmp_path / "prompts",
            resources_config_path=config_path,
        )
        result = loader.load("test.md")
        assert result == "값: {{UNKNOWN_VAR}}"

    def test_missing_resource_file_graceful(self, tmp_path: Path) -> None:
        """resource 파일 없으면 빈 문자열로 매핑 + 경고 (raise 안 함)."""
        _write_prompt(tmp_path, "test.md", "톤: [{{TONE_REFERENCE}}]끝")
        config_path = _write_resources_config(
            tmp_path,
            {
                "TONE_REFERENCE": {
                    "source_type": "file",
                    "path": str(tmp_path / "absent.md"),  # 존재하지 않는 파일
                }
            },
        )

        loader = PromptLoader(
            prompts_dir=tmp_path / "prompts",
            resources_config_path=config_path,
        )
        # raise 없이 정상 동작
        result = loader.load("test.md")
        # 빈 문자열로 치환되어 placeholder 가 사라짐
        assert result == "톤: []끝"

    def test_extra_vars_runtime(self, tmp_path: Path) -> None:
        """``substitute`` 메서드에 extra_vars 전달 시 정상 치환."""
        config_path = _write_resources_config(tmp_path, {})
        loader = PromptLoader(
            prompts_dir=tmp_path,
            resources_config_path=config_path,
        )
        result = loader.substitute(
            "안녕 {{NAME}}, {{GREETING}}",
            extra_vars={"NAME": "지훈", "GREETING": "반갑다"},
        )
        assert result == "안녕 지훈, 반갑다"


# =====================================================================
# WhitelistedSubstitutor 테스트
# =====================================================================
class TestWhitelistedSubstitutor:

    def test_whitelisted_only_substituted(self) -> None:
        """placeholder_locations 에 있는 것만 치환."""
        html = '<img src="{{HERO_IMAGE_URL}}"><a href="{{CTA_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values = {
            "HERO_IMAGE_URL": "https://example.com/hero.jpg",
            "CTA_URL": "https://ignored.com",
        }

        sub = WhitelistedSubstitutor()
        result, substituted, preserved = sub.substitute(html, locations, values)

        assert "https://example.com/hero.jpg" in result
        assert "{{CTA_URL}}" in result  # locations 에 없으므로 보존
        assert "HERO_IMAGE_URL" in substituted
        assert "CTA_URL" in preserved

    def test_comment_internal_preserved(self) -> None:
        """HTML 주석 내부의 ``{{VAR}}`` 는 보존 (locations 에 있어도)."""
        html = (
            "<!-- {{HERO_IMAGE_URL}}: 히어로 이미지 자리 -->"
            '<img src="{{HERO_IMAGE_URL}}">'
        )
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values = {"HERO_IMAGE_URL": "https://example.com/hero.jpg"}

        sub = WhitelistedSubstitutor()
        result, _, _ = sub.substitute(html, locations, values)

        # 주석 내부는 그대로
        assert "<!-- {{HERO_IMAGE_URL}}: 히어로 이미지 자리 -->" in result
        # 주석 외부는 치환됨
        assert 'src="https://example.com/hero.jpg"' in result

    def test_non_outside_comment_zone_skipped(self) -> None:
        """render_zone != outside_comment 인 항목은 치환 안 함."""
        html = '<img src="{{HERO_IMAGE_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "inside_comment"}
        ]
        values = {"HERO_IMAGE_URL": "https://example.com/hero.jpg"}

        sub = WhitelistedSubstitutor()
        result, substituted, preserved = sub.substitute(html, locations, values)

        assert "{{HERO_IMAGE_URL}}" in result  # 그대로 보존
        assert "HERO_IMAGE_URL" in preserved
        assert "HERO_IMAGE_URL" not in substituted

    def test_missing_value_preserved(self) -> None:
        """locations 에 있어도 values 에 키 없으면 보존."""
        html = '<img src="{{HERO_IMAGE_URL}}">'
        locations = [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ]
        values: dict[str, str] = {}  # 비어있음

        sub = WhitelistedSubstitutor()
        result, _, preserved = sub.substitute(html, locations, values)

        assert "{{HERO_IMAGE_URL}}" in result
        assert "HERO_IMAGE_URL" in preserved

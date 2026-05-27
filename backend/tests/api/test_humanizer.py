"""humanizer 단위 테스트 (7건).

명세: docs/patches/2026-05-28_b3-s3-c_trace_viewer.md §11-1.
"""
from __future__ import annotations

import pytest

from backend.api.services import humanizer
from backend.api.services.humanizer import (
    _MAX_LEN,
    _summarize,
    get_all_personas,
    get_persona,
    humanize,
    load_personas,
)


@pytest.fixture(autouse=True)
def _reset_persona_cache():
    """각 테스트 전후 lru_cache 비움 — 모킹 / yaml 수정 격리."""
    load_personas.cache_clear()
    humanizer._alias_map.cache_clear()
    yield
    load_personas.cache_clear()
    humanizer._alias_map.cache_clear()


class TestHumanizer:
    def test_1_load_personas_has_9_and_3(self):
        data = load_personas()
        assert "personas" in data and "stages" in data
        assert len(data["personas"]) == 9
        assert len(data["stages"]) == 3
        # 짧은 id (trace_converter 와 동일) 사용
        for key in ["scout", "analyst", "planner", "writer", "factchecker",
                    "devils", "editor", "architect", "builder"]:
            assert key in data["personas"], f"persona {key} 누락"

    def test_2_determinism(self):
        raw = "오늘은 AI 규제 이슈가 떠올랐습니다. 빅테크들이 대응 중입니다."
        a = humanize("scout", raw)
        b = humanize("scout", raw)
        c = humanize("scout", raw)
        assert a == b == c
        assert a != ""

    def test_3_unknown_agent_falls_back_to_summary_only(self):
        raw = "어떤 텍스트입니다."
        result = humanize("does_not_exist_999", raw)
        # 짧은 raw 가 그대로 summarize 결과로
        assert result == _summarize(raw)
        # 알 수 없는 페르소나 → prefix/suffix 부착 안 됨
        scout_result = humanize("scout", raw)
        assert scout_result != result

    def test_4_empty_raw_text(self):
        # 빈 raw → body 가 비어 있으므로 prefix + suffix 만 남거나 빈 문자열
        result = humanize("writer", "")
        # 절대 예외 발생하지 않아야 함
        assert isinstance(result, str)
        assert len(result) <= _MAX_LEN

    def test_5_very_long_raw_text_capped(self):
        raw = "긴 텍스트. " * 500  # ~2500자
        result = humanize("writer", raw)
        assert len(result) <= _MAX_LEN

    def test_6_json_code_fence_stripped(self):
        raw = "```json\n{\"topic\": \"AI\"}\n```\n핵심 결과입니다."
        result = humanize("scout", raw)
        # 코드 펜스 마커 자체는 제거되어야 함
        assert "```" not in result
        # 본문은 살아 있어야 함 (페르소나 prefix/suffix 와 함께)
        assert "결과" in result or "핵심" in result

    def test_7_alias_resolves_to_canonical(self):
        # personas.yaml 의 aliases 에 등록된 풀네임도 동일하게 변환
        raw = "트렌드 잡았습니다. AI 규제."
        short = humanize("scout", raw)
        full = humanize("trend_scout", raw)
        assert short == full
        # get_persona 도 alias 로 조회 가능해야 함
        assert get_persona("trend_scout") is not None
        assert get_persona("scout") == get_persona("trend_scout")

    def test_8_get_all_personas_shape(self):
        data = get_all_personas()
        for key, p in data["personas"].items():
            for field in ["display_name", "emoji", "stage", "color_hex", "speech"]:
                assert field in p, f"{key} 에 {field} 누락"
            sp = p["speech"]
            assert "prefix_options" in sp and "suffix_options" in sp

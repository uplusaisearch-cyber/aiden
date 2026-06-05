"""B4-S2 C3: Strategy Planner INJECTED_* 동적 주입 테스트.

명세: docs/patches/2026-06-06_B4-S2_topic-angle-seg_v2.md §C3
- selection 활성 시 4개 키가 한글 라벨 / 지시문 / 페르소나로 채워짐
- selection None 시 4개 키 모두 빈 문자열 → 프롬프트 폴백 분기 발동
- PromptLoader.substitute 가 4개 placeholder 를 실제로 치환
"""
from __future__ import annotations

from backend.agents.concrete_agents import _planner_dynamic_vars_factory
from backend.core.base_agent import PromptLoader


class TestPlannerDynamicVarsFactory:
    SAMPLE_SELECTION = {
        "angle": "contrast",
        "angle_label": "대조/충돌",
        "angle_directive": "통념을 뒤집는 반대 시각으로 접근",
        "audience_segment": "thirties_single",
        "segment_label": "30대 1인가구",
        "segment_persona": "자기투자·편의·시간 절약 중시",
    }

    EXPECTED_KEYS = {
        "INJECTED_ANGLE",
        "INJECTED_ANGLE_DIRECTIVE",
        "INJECTED_SEGMENT",
        "INJECTED_SEGMENT_PERSONA",
    }

    def test_1_selection_active_populates_labels_and_directives(self):
        """selection 활성 시 4개 키가 한글 라벨/지시문/페르소나로 채워짐."""
        fn = _planner_dynamic_vars_factory(self.SAMPLE_SELECTION)
        out = fn()
        assert set(out.keys()) == self.EXPECTED_KEYS
        assert out["INJECTED_ANGLE"] == "대조/충돌"
        assert out["INJECTED_ANGLE_DIRECTIVE"] == "통념을 뒤집는 반대 시각으로 접근"
        assert out["INJECTED_SEGMENT"] == "30대 1인가구"
        assert out["INJECTED_SEGMENT_PERSONA"] == "자기투자·편의·시간 절약 중시"

    def test_2_none_selection_yields_empty_strings(self):
        """selection None 시 4개 키 모두 빈 문자열 — 폴백 분기 발동 보장."""
        fn = _planner_dynamic_vars_factory(None)
        out = fn()
        assert set(out.keys()) == self.EXPECTED_KEYS
        for k in self.EXPECTED_KEYS:
            assert out[k] == "", f"{k} 가 비어있지 않음: {out[k]!r}"

    def test_3_partial_selection_missing_keys_become_empty(self):
        """selection dict 에 일부 키만 있어도 누락 키는 빈 문자열."""
        partial = {"angle": "contrast", "angle_label": "대조/충돌"}  # directive/segment 누락
        out = _planner_dynamic_vars_factory(partial)()
        assert out["INJECTED_ANGLE"] == "대조/충돌"
        assert out["INJECTED_ANGLE_DIRECTIVE"] == ""
        assert out["INJECTED_SEGMENT"] == ""
        assert out["INJECTED_SEGMENT_PERSONA"] == ""

    def test_4_promptloader_substitutes_all_4_placeholders(self):
        """PromptLoader.substitute 가 prompt 안 {{INJECTED_*}} 4개를 실제로 치환."""
        tpl = (
            "angle: {{INJECTED_ANGLE}}\n"
            "directive: {{INJECTED_ANGLE_DIRECTIVE}}\n"
            "segment: {{INJECTED_SEGMENT}}\n"
            "persona: {{INJECTED_SEGMENT_PERSONA}}\n"
        )
        loader = PromptLoader()
        extra = _planner_dynamic_vars_factory(self.SAMPLE_SELECTION)()
        result = loader.substitute(tpl, extra_vars=extra)
        assert "{{INJECTED_ANGLE}}" not in result
        assert "{{INJECTED_ANGLE_DIRECTIVE}}" not in result
        assert "{{INJECTED_SEGMENT}}" not in result
        assert "{{INJECTED_SEGMENT_PERSONA}}" not in result
        assert "대조/충돌" in result
        assert "통념을 뒤집는 반대 시각으로 접근" in result
        assert "30대 1인가구" in result
        assert "자기투자·편의·시간 절약 중시" in result

    def test_5_fallback_substitution_yields_empty_quoted_values(self):
        """selection None → substitute 결과의 placeholder 위치는 빈 문자열.

        프롬프트의 활성 조건("4개 값이 모두 비어있지 않으면") 검사가 폴백 분기를
        발동시키도록 빈 문자열이 정확히 produce 되는지 검증.
        """
        tpl = '지정 angle: "{{INJECTED_ANGLE}}"\n지시문: "{{INJECTED_ANGLE_DIRECTIVE}}"'
        loader = PromptLoader()
        extra = _planner_dynamic_vars_factory(None)()
        result = loader.substitute(tpl, extra_vars=extra)
        assert '지정 angle: ""' in result
        assert '지시문: ""' in result

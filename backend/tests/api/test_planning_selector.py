"""B4-S2 PlanningSelector unit tests.

명세: docs/patches/2026-06-06_B4-S2_topic-angle-seg_v2.md §C1
- angle 순환 (enabled=true만)
- event_tie 제외
- segment 순환
"""
from __future__ import annotations

import pytest

from backend.api.services.planning_selector import PlanningSelector


@pytest.fixture
def selector():
    """매 테스트마다 격리된 selector 인스턴스 (singleton reset)."""
    PlanningSelector.reset_instance()
    s = PlanningSelector()
    yield s
    PlanningSelector.reset_instance()


class TestPlanningSelector:
    def test_1_angle_round_robin_cycles_all_enabled(self, selector):
        """enabled angle 8종이 순서대로 순환, 9번째 호출은 첫 angle 로 회귀."""
        enabled_keys = [a["key"] for a in selector._angles if a.get("enabled") is True]
        assert len(enabled_keys) == 8, "event_tie 1개 제외 후 8종이어야 함"
        seen = [selector.select("food")["angle"] for _ in range(len(enabled_keys))]
        assert seen == enabled_keys, f"순환 순서 어긋남: {seen}"

        # 한 바퀴 후 첫 angle 로 회귀
        assert selector.select("food")["angle"] == enabled_keys[0]

    def test_2_event_tie_never_selected(self, selector):
        """event_tie 는 enabled=false → 어떤 호출에서도 선택되지 않음."""
        seen_angles = {selector.select("food")["angle"] for _ in range(20)}
        assert "event_tie" not in seen_angles
        # 동시에, 다른 8종은 모두 한 번 이상 등장해야 함 (20회면 2바퀴 이상).
        assert len(seen_angles) == 8

    def test_3_segment_rotates(self, selector):
        """segment 7종이 순서대로 회전 후 첫 항목으로 회귀."""
        segment_keys = [s["key"] for s in selector._segments]
        assert len(segment_keys) == 7
        seen = [
            selector.select("food")["audience_segment"]
            for _ in range(len(segment_keys))
        ]
        assert seen == segment_keys

        assert selector.select("food")["audience_segment"] == segment_keys[0]

    def test_4_selection_payload_has_all_keys(self, selector):
        """반환 dict 가 명세된 6개 키를 모두 가지고 비어있지 않음."""
        result = selector.select("food")
        expected_keys = {
            "angle",
            "angle_label",
            "angle_directive",
            "audience_segment",
            "segment_label",
            "segment_persona",
        }
        assert set(result.keys()) == expected_keys
        for k, v in result.items():
            assert isinstance(v, str) and v, f"{k} 가 비어있음: {v!r}"

    def test_5_category_does_not_affect_global_rotation(self, selector):
        """이번 범위는 글로벌 순환 — category 가 달라도 카운터 공유.

        v2 에서 category 별 카운터 도입 시 본 테스트는 수정 예정.
        """
        first = selector.select("food")
        second = selector.select("ai-trend")
        # 다른 category 라도 angle/segment 카운터는 1씩 진행됨
        assert first["angle"] != second["angle"]
        assert first["audience_segment"] != second["audience_segment"]

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


class TestPlanningSelectorOverride:
    """build_with_override: 사용자 명시 + 자동 회전 혼합 모드."""

    @pytest.fixture
    def selector(self):
        PlanningSelector.reset_instance()
        s = PlanningSelector()
        yield s
        PlanningSelector.reset_instance()

    def test_1_full_override_does_not_advance_counters(self, selector):
        """둘 다 명시 → angle/segment 카운터 진행 X (다음 자동 사용자 영향 0)."""
        result = selector.build_with_override(
            "food",
            {"angle": "contrast", "audience_segment": "thirties_single"},
        )
        assert result["angle"] == "contrast"
        assert result["angle_label"] == "대조/충돌"
        assert result["audience_segment"] == "thirties_single"
        assert result["segment_label"] == "30대 1인가구"
        # 카운터는 그대로 0
        assert selector._angle_idx == 0
        assert selector._segment_idx == 0
        # 곧이어 자동 호출하면 첫 enabled angle / 첫 segment 가 나와야 함
        nxt = selector.select("food")
        enabled_keys = [a["key"] for a in selector._angles if a.get("enabled") is True]
        assert nxt["angle"] == enabled_keys[0]
        assert nxt["audience_segment"] == selector._segments[0]["key"]

    def test_2_partial_override_only_angle_advances_segment_counter(self, selector):
        """angle 만 명시 → segment 카운터만 진행."""
        result = selector.build_with_override(
            "food",
            {"angle": "ranking", "audience_segment": None},
        )
        assert result["angle"] == "ranking"
        # segment 는 자동 회전 — 첫 segment
        assert result["audience_segment"] == selector._segments[0]["key"]
        # angle 카운터는 0, segment 카운터는 1
        assert selector._angle_idx == 0
        assert selector._segment_idx == 1

    def test_3_partial_override_only_segment_advances_angle_counter(self, selector):
        """segment 만 명시 → angle 카운터만 진행."""
        result = selector.build_with_override(
            "food",
            {"angle": None, "audience_segment": "side_hustler"},
        )
        assert result["audience_segment"] == "side_hustler"
        enabled_keys = [a["key"] for a in selector._angles if a.get("enabled") is True]
        # 첫 enabled angle 자동 선택
        assert result["angle"] == enabled_keys[0]
        assert selector._angle_idx == 1
        assert selector._segment_idx == 0

    def test_4_invalid_angle_key_raises(self, selector):
        """presets.json 에 없는 angle key → ValueError."""
        with pytest.raises(ValueError, match="angle key 미정의"):
            selector.build_with_override(
                "food",
                {"angle": "nonexistent_angle", "audience_segment": None},
            )

    def test_5_disabled_angle_is_rejected(self, selector):
        """enabled=false 인 angle 은 명시 선택도 차단 (event_tie 등)."""
        with pytest.raises(ValueError, match="비활성"):
            selector.build_with_override(
                "food",
                {"angle": "event_tie", "audience_segment": None},
            )

    def test_6_invalid_segment_key_raises(self, selector):
        """presets.json 에 없는 segment key → ValueError."""
        with pytest.raises(ValueError, match="segment key 미정의"):
            selector.build_with_override(
                "food",
                {"angle": None, "audience_segment": "nonexistent_seg"},
            )

    def test_7_list_presets_shape(self, selector):
        """list_presets() 가 모달 노출에 필요한 9 angles + 7 segments 반환 + enabled 플래그."""
        presets = selector.list_presets()
        assert set(presets.keys()) == {"angles", "segments"}
        assert len(presets["angles"]) == 9
        assert len(presets["segments"]) == 7
        # 각 angle 에 enabled 플래그 존재
        for a in presets["angles"]:
            assert set(a.keys()) == {"key", "label", "directive", "enabled"}
        # event_tie 는 enabled=False
        evt = next(a for a in presets["angles"] if a["key"] == "event_tie")
        assert evt["enabled"] is False
        # 나머지 8개는 enabled=True
        enabled_count = sum(1 for a in presets["angles"] if a["enabled"])
        assert enabled_count == 8

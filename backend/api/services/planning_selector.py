"""B4-S2 Planning Selector — in-memory round-robin.

명세: docs/patches/2026-06-06_B4-S2_topic-angle-seg_v2.md §C1

- ``backend/config/planning_presets.json`` 로드 (angle 9 / audience_segments 7 / rotation)
  ※ 원 명세 경로는 ``data/`` 였으나 ``.gitignore`` 가 ``data/`` 통째 ignore 라
     repo-seeded 형상자산이 deploy 컨테이너에 적재 안 되는 차단 회피 위해 이동.
- 모듈 레벨 카운터로 angle (``enabled=true`` 만) + segment 회전
- redeploy 시 리셋 허용 (v2 영속화 — Volume/DB 백로그)
- 단일 worker 가정. ``threading.Lock`` 으로 카운터 직렬화.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import TypedDict

from backend.core.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

PRESETS_PATH: Path = PROJECT_ROOT / "backend" / "config" / "planning_presets.json"


class Selection(TypedDict):
    angle: str
    angle_label: str
    angle_directive: str
    audience_segment: str
    segment_label: str
    segment_persona: str


class PlanningSelector:
    """angle round-robin + segment rotate 카운터.

    싱글톤. ``instance()`` 로 접근. 테스트 격리는 ``reset_instance()``.
    """

    _instance: "PlanningSelector | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, presets_path: Path = PRESETS_PATH) -> None:
        self._path = presets_path
        self._lock = threading.Lock()
        self._angle_idx = 0
        self._segment_idx = 0
        self._load()

    @classmethod
    def instance(cls) -> "PlanningSelector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """테스트 격리용. 프로덕션 호출 금지."""
        with cls._instance_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # 내부 로드
    # ------------------------------------------------------------------
    def _load(self) -> None:
        raw = self._path.read_text(encoding="utf-8")
        data = json.loads(raw)
        self._angles: list[dict] = data.get("angles", [])
        self._segments: list[dict] = data.get("audience_segments", [])
        self._rotation: dict = data.get("rotation", {})
        enabled_count = sum(1 for a in self._angles if a.get("enabled") is True)
        logger.info(
            "PlanningSelector loaded: angles=%d (enabled=%d), segments=%d",
            len(self._angles),
            enabled_count,
            len(self._segments),
        )

    def _enabled_angles(self) -> list[dict]:
        return [a for a in self._angles if a.get("enabled") is True]

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def select(self, category: str) -> Selection:
        """다음 angle + segment 조합 반환 (round-robin 카운터 진행).

        ``category`` 는 현재 회전 로직에 영향 없음(이번 범위는 글로벌 단순 순환).
        v2 에서 category 별 카운터 / dedup_window 도입 시 본 인자가 분기 키로 확장.
        """
        with self._lock:
            enabled = self._enabled_angles()
            if not enabled:
                raise RuntimeError("planning_presets.json: enabled angle 0개")
            if not self._segments:
                raise RuntimeError("planning_presets.json: segment 0개")

            angle = enabled[self._angle_idx % len(enabled)]
            segment = self._segments[self._segment_idx % len(self._segments)]
            self._angle_idx += 1
            self._segment_idx += 1

        logger.info(
            "selector select category=%s → angle=%s segment=%s",
            category, angle["key"], segment["key"],
        )
        return Selection(
            angle=angle["key"],
            angle_label=angle["label"],
            angle_directive=angle["directive"],
            audience_segment=segment["key"],
            segment_label=segment["label"],
            segment_persona=segment["persona"],
        )

    def build_with_override(
        self,
        category: str,
        override: dict[str, str | None],
    ) -> Selection:
        """사용자 명시 + 자동 회전 혼합 모드.

        ``override["angle"]`` / ``override["audience_segment"]`` 중:
          - None 또는 누락 → 자동 회전 (해당 카운터 진행, 기존 자동 사용자에게 영향 0)
          - 유효한 key → 해당 preset 사용 (카운터 진행 X, 다른 자동 사용자 회전 순서 보존)
          - presets.json 에 없는 key → ValueError

        둘 다 명시 시 selector 카운터는 전혀 진행되지 않는다.
        """
        if not self._enabled_angles():
            raise RuntimeError("planning_presets.json: enabled angle 0개")
        if not self._segments:
            raise RuntimeError("planning_presets.json: segment 0개")

        angle_key = override.get("angle")
        segment_key = override.get("audience_segment")

        # angle 분기
        if angle_key:
            angle = next(
                (a for a in self._angles if a.get("key") == angle_key),
                None,
            )
            if angle is None:
                raise ValueError(f"angle key 미정의: {angle_key!r}")
            if angle.get("enabled") is not True:
                # disabled (event_tie 등) — 자동 흐름에선 제외되지만 사용자가 명시했으면 허용.
                # 다만 명시적으로 enabled=False 인 angle 도 허용할지는 v2 정책. 현재는 차단.
                raise ValueError(
                    f"angle key 비활성 — 사용 불가: {angle_key!r}"
                )
        else:
            # 자동 — 카운터 진행
            with self._lock:
                enabled = self._enabled_angles()
                angle = enabled[self._angle_idx % len(enabled)]
                self._angle_idx += 1

        # segment 분기
        if segment_key:
            segment = next(
                (s for s in self._segments if s.get("key") == segment_key),
                None,
            )
            if segment is None:
                raise ValueError(f"segment key 미정의: {segment_key!r}")
        else:
            with self._lock:
                segment = self._segments[self._segment_idx % len(self._segments)]
                self._segment_idx += 1

        logger.info(
            "selector override category=%s angle=%s(%s) segment=%s(%s)",
            category,
            angle["key"], "manual" if angle_key else "auto",
            segment["key"], "manual" if segment_key else "auto",
        )
        return Selection(
            angle=angle["key"],
            angle_label=angle["label"],
            angle_directive=angle["directive"],
            audience_segment=segment["key"],
            segment_label=segment["label"],
            segment_persona=segment["persona"],
        )

    def list_presets(self) -> dict[str, list[dict]]:
        """프론트 모달에서 선택지 노출용. ``enabled`` 플래그 그대로 노출.

        - angles: 9종 전체 + enabled 플래그 (UI 측에서 disabled 항목 회색 처리/숨김)
        - segments: 7종 전체
        - rotation: 회전 정책 (UI 표시용 메타)
        """
        return {
            "angles": [
                {
                    "key": a["key"],
                    "label": a["label"],
                    "directive": a["directive"],
                    "enabled": bool(a.get("enabled")),
                }
                for a in self._angles
            ],
            "segments": [
                {
                    "key": s["key"],
                    "label": s["label"],
                    "persona": s["persona"],
                }
                for s in self._segments
            ],
        }

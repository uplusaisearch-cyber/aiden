"""Judge Panel 모델 해석기 (3단계 우선순위).

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md

런타임 모델 선택 우선순위:
    1. 어드민 UI 런타임 override (B3-S3 영역, 본 모듈은 hook 제공)
    2. 환경변수 (JUDGE_GEMINI_MODEL / JUDGE_GPT_MODEL / JUDGE_CLAUDE_MODEL)
    3. config/agents.yaml 의 judge_panel.models 기본값

가중치 검증은 startup 시 settings.py 가 호출.
"""
from __future__ import annotations

import os

ResolutionSource = str  # "runtime_override" | "env" | "config"


def _runtime_key(judge_name: str) -> str:
    return f"{judge_name}_model"


def _env_key(judge_name: str) -> str:
    return f"JUDGE_{judge_name.upper()}_MODEL"


def resolve_judge_model(
    judge_name: str,
    *,
    runtime_override: dict | None,
    config_defaults: dict[str, str],
) -> tuple[str, ResolutionSource]:
    """3단계 우선순위로 모델 ID 와 해석 출처를 반환.

    Args:
        judge_name: "gemini" | "gpt" | "claude"
        runtime_override: 어드민 UI 에서 주입된 dict.
            형식: ``{"gemini_model": "...", "gpt_model": "...", "claude_model": "..."}``.
            전체 None 또는 해당 키가 없으면 다음 단계로 fallback.
        config_defaults: ``config/agents.yaml`` 의 ``judge_panel.models`` 섹션
            (예: ``{"gemini": "gemini-2.5-pro", ...}``).

    Returns:
        (model_id, source) 튜플. source 는 "runtime_override"/"env"/"config" 중 하나.

    Raises:
        KeyError: config_defaults 에도 judge_name 이 없는 경우.
    """
    # 1) 어드민 UI 런타임 override
    if runtime_override:
        key = _runtime_key(judge_name)
        value = runtime_override.get(key)
        if value:
            return value, "runtime_override"

    # 2) 환경변수 (.env)
    env_value = os.getenv(_env_key(judge_name))
    if env_value:  # 빈 문자열은 미설정 취급
        return env_value, "env"

    # 3) config 기본값
    if judge_name not in config_defaults:
        raise KeyError(
            f"judge_name='{judge_name}' 에 대한 기본 모델이 config/agents.yaml 의 "
            f"judge_panel.models 섹션에 없습니다."
        )
    return config_defaults[judge_name], "config"


def validate_judge_weights(weights: dict[str, float]) -> None:
    """평가 차원 가중치 합이 100인지 검증 (startup 시 호출).

    Args:
        weights: 5개 차원 → 가중치 매핑.

    Raises:
        ValueError: 합이 100이 아니거나 음수 가중치 존재 시.
    """
    if any(v < 0 for v in weights.values()):
        raise ValueError(f"Judge 가중치에 음수가 있습니다: {weights}")
    total = sum(weights.values())
    # 부동소수 오차 허용 (소수 둘째 자리)
    if abs(total - 100) > 0.01:
        raise ValueError(
            f"Judge 가중치 합이 100이 아닙니다: {total} (weights={weights}). "
            "config/agents.yaml 의 judge_panel.weights 또는 "
            "JUDGE_WEIGHTS_* 환경변수를 확인하세요."
        )

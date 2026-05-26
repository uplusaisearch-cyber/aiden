"""judge_model_resolver 3단계 우선순위 + 가중치 검증 단위 테스트 (5건).

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md
"""
from __future__ import annotations

import pytest

from backend.core.judge_model_resolver import (
    resolve_judge_model,
    validate_judge_weights,
)


CONFIG_DEFAULTS = {
    "gemini": "gemini-2.5-pro",
    "gpt": "gpt-5",
    "claude": "claude-opus-4-7",
}


class TestResolveJudgeModel:
    """3단계 우선순위: runtime_override > env > config."""

    def test_runtime_override_wins(self, monkeypatch):
        """#1: runtime_override 가 있으면 env/config 보다 우선."""
        monkeypatch.setenv("JUDGE_GEMINI_MODEL", "from-env-model")
        runtime_override = {"gemini_model": "from-ui-runtime"}

        model_id, source = resolve_judge_model(
            "gemini",
            runtime_override=runtime_override,
            config_defaults=CONFIG_DEFAULTS,
        )
        assert model_id == "from-ui-runtime"
        assert source == "runtime_override"

    def test_env_used_when_no_runtime_override(self, monkeypatch):
        """#2: runtime_override 없고 env 있으면 env."""
        monkeypatch.setenv("JUDGE_GPT_MODEL", "gpt-from-env")

        model_id, source = resolve_judge_model(
            "gpt",
            runtime_override=None,
            config_defaults=CONFIG_DEFAULTS,
        )
        assert model_id == "gpt-from-env"
        assert source == "env"

    def test_config_default_when_nothing_else(self, monkeypatch):
        """#3: runtime_override·env 모두 없으면 config 기본값."""
        monkeypatch.delenv("JUDGE_CLAUDE_MODEL", raising=False)

        model_id, source = resolve_judge_model(
            "claude",
            runtime_override=None,
            config_defaults=CONFIG_DEFAULTS,
        )
        assert model_id == "claude-opus-4-7"
        assert source == "config"

    def test_resolution_source_labels_are_exact(self, monkeypatch):
        """#4: models_resolution_source 라벨이 정확히 "runtime_override"/"env"/"config"."""
        monkeypatch.delenv("JUDGE_GEMINI_MODEL", raising=False)
        monkeypatch.setenv("JUDGE_GPT_MODEL", "envgpt")
        monkeypatch.delenv("JUDGE_CLAUDE_MODEL", raising=False)
        runtime_override = {"claude_model": "ui-claude"}

        _, src_gem = resolve_judge_model(
            "gemini", runtime_override=runtime_override, config_defaults=CONFIG_DEFAULTS,
        )
        _, src_gpt = resolve_judge_model(
            "gpt", runtime_override=runtime_override, config_defaults=CONFIG_DEFAULTS,
        )
        _, src_claude = resolve_judge_model(
            "claude", runtime_override=runtime_override, config_defaults=CONFIG_DEFAULTS,
        )
        assert src_gem == "config"
        assert src_gpt == "env"
        assert src_claude == "runtime_override"


class TestValidateJudgeWeights:
    """startup 시 가중치 합 검증."""

    def test_weights_sum_not_100_raises(self):
        """#5: 가중치 합 != 100 → ValueError."""
        weights = {
            "topic_fit": 20,
            "content_quality": 25,
            "interactivity": 15,
            "tone_authenticity": 20,
            "timeliness_trust": 10,  # 합 = 90
        }
        with pytest.raises(ValueError, match="100"):
            validate_judge_weights(weights)

"""JudgePanel 오케스트레이터 단위 테스트 (8건).

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import pytest

from backend.orchestrators.judge_panel import JudgePanel


# =====================================================================
# 공통 픽스처
# =====================================================================
DIMENSIONS = (
    "topic_fit",
    "content_quality",
    "interactivity",
    "tone_authenticity",
    "timeliness_trust",
)

TEST_CONFIG: dict[str, Any] = {
    "models": {
        "gemini": "gemini-2.5-pro",
        "gpt": "gpt-5",
        "claude": "claude-opus-4-7",
    },
    "weights": {
        "topic_fit": 20,
        "content_quality": 25,
        "interactivity": 15,
        "tone_authenticity": 20,
        "timeliness_trust": 20,
    },
    "budget_per_run_usd": 0.05,
    "timeout_sec": 10,
}
TEST_PROMPTS = {"gemini": "GP", "gpt": "OP", "claude": "AP"}


def _make_eval(model_id: str, scores: dict[str, int]) -> dict[str, Any]:
    """공통 JSON 스키마 dict 생성."""
    return {
        "model": model_id,
        "scores": dict(scores),
        "comments": {k: f"comment for {k}" for k in scores},
        "overall_score": round(sum(scores.values()) / len(scores), 1),
        "strengths": ["s1", "s2"],
        "weaknesses": ["w1"],
        "one_line_verdict": "한줄평",
    }


def make_success_fn(scores: dict[str, int], latency: float = 0.01):
    async def fn(*, model_id, system_prompt, user_prompt):
        await asyncio.sleep(latency)
        return _make_eval(model_id, scores)
    return fn


def make_fail_fn(exc: BaseException):
    async def fn(*, model_id, system_prompt, user_prompt):
        raise exc
    return fn


def _build_panel(judge_fns: dict, runtime_override=None) -> JudgePanel:
    return JudgePanel(
        config=TEST_CONFIG,
        prompts=TEST_PROMPTS,
        judge_fns=judge_fns,
        runtime_override=runtime_override,
    )


SAMPLE_HTML = "<html><body><h1>test content</h1><p>본문</p></body></html>"


# =====================================================================
# 8건
# =====================================================================
class TestJudgePanel:

    @pytest.mark.asyncio
    async def test_1_happy_path_all_three_succeed(self):
        """#1: 3 모델 모두 성공 → aggregate 정확 계산, status=completed."""
        gemini_scores = {"topic_fit": 8, "content_quality": 8, "interactivity": 8,
                         "tone_authenticity": 7, "timeliness_trust": 8}
        gpt_scores = {"topic_fit": 7, "content_quality": 8, "interactivity": 8,
                      "tone_authenticity": 7, "timeliness_trust": 7}
        claude_scores = {"topic_fit": 8, "content_quality": 7, "interactivity": 8,
                         "tone_authenticity": 7, "timeliness_trust": 8}
        panel = _build_panel({
            "gemini": make_success_fn(gemini_scores),
            "gpt": make_success_fn(gpt_scores),
            "claude": make_success_fn(claude_scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["status"] == "completed"
        assert result["failed_models"] == []
        assert set(result["evaluations"].keys()) == {"gemini", "gpt", "claude"}
        agg = result["aggregate"]
        # topic_fit: (8+7+8)/3 = 7.67
        assert agg["mean_scores"]["topic_fit"] == pytest.approx(7.67, abs=0.01)
        assert agg["mean_scores"]["content_quality"] == pytest.approx(7.67, abs=0.01)
        # weighted_total: sum(mean*w)/10 — 평균이 7.6 근처면 76 근처
        assert 70 <= agg["weighted_total"] <= 80
        assert result["input_size_bytes"] == len(SAMPLE_HTML.encode("utf-8"))
        assert result["models_used"] == TEST_CONFIG["models"]

    @pytest.mark.asyncio
    async def test_2_one_model_fails_degraded(self):
        """#2: 1 모델 실패 (rate limit 모방) → 2 모델 평균, status=degraded."""
        scores = {d: 7 for d in DIMENSIONS}
        panel = _build_panel({
            "gemini": make_success_fn(scores),
            "gpt": make_fail_fn(RuntimeError("openai rate limit")),
            "claude": make_success_fn(scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["status"] == "degraded"
        assert result["failed_models"] == ["gpt"]
        assert set(result["evaluations"].keys()) == {"gemini", "claude"}
        # mean 은 2개 평균
        assert result["aggregate"]["mean_scores"]["topic_fit"] == 7.0

    @pytest.mark.asyncio
    async def test_3_two_models_fail_degraded(self):
        """#3: 2 모델 실패 → status=degraded, evaluations 1개만 보존."""
        scores = {d: 6 for d in DIMENSIONS}
        panel = _build_panel({
            "gemini": make_fail_fn(RuntimeError("gemini down")),
            "gpt": make_fail_fn(RuntimeError("openai down")),
            "claude": make_success_fn(scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["status"] == "degraded"
        assert sorted(result["failed_models"]) == ["gemini", "gpt"]
        assert set(result["evaluations"].keys()) == {"claude"}
        assert result["aggregate"]["mean_scores"]["topic_fit"] == 6.0

    @pytest.mark.asyncio
    async def test_4_all_three_fail_status_failed(self):
        """#4: 3 모델 모두 실패 → status=failed."""
        panel = _build_panel({
            "gemini": make_fail_fn(RuntimeError("g")),
            "gpt": make_fail_fn(RuntimeError("o")),
            "claude": make_fail_fn(RuntimeError("a")),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["status"] == "failed"
        assert sorted(result["failed_models"]) == ["claude", "gemini", "gpt"]
        assert result["evaluations"] == {}
        assert result["aggregate"] is None

    @pytest.mark.asyncio
    async def test_5_json_parse_error_isolated(self):
        """#5: JSON 파싱 실패(1 모델) → 해당 모델만 failed 처리."""
        scores = {d: 7 for d in DIMENSIONS}
        panel = _build_panel({
            "gemini": make_success_fn(scores),
            "gpt": make_fail_fn(json.JSONDecodeError("not json", "doc", 0)),
            "claude": make_success_fn(scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["status"] == "degraded"
        assert result["failed_models"] == ["gpt"]
        assert set(result["evaluations"].keys()) == {"gemini", "claude"}

    @pytest.mark.asyncio
    async def test_6_outlier_detection_high(self):
        """#6: outlier 감지 (high severity).

        명세 예시(판정 결과 high 인 케이스)와 동일한 점수 분포:
        tone_authenticity = (gemini 8, gpt 6, claude 4) → mean=6.0, delta(claude)=-2.0.
        """
        gemini_scores = {**{d: 8 for d in DIMENSIONS}, "tone_authenticity": 8}
        gpt_scores = {**{d: 7 for d in DIMENSIONS}, "tone_authenticity": 6}
        claude_scores = {**{d: 7 for d in DIMENSIONS}, "tone_authenticity": 4}

        panel = _build_panel({
            "gemini": make_success_fn(gemini_scores),
            "gpt": make_success_fn(gpt_scores),
            "claude": make_success_fn(claude_scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        outliers = result["aggregate"]["outliers"]
        tone_outliers = [o for o in outliers if o["dimension"] == "tone_authenticity"]
        assert len(tone_outliers) >= 1, (
            f"tone_authenticity outlier 가 잡히지 않음. outliers={outliers}, "
            f"aggregate={result['aggregate']}"
        )
        claude_outlier = next((o for o in tone_outliers if o["model"] == "claude"), None)
        assert claude_outlier is not None
        assert claude_outlier["score"] == 4
        assert claude_outlier["mean"] == pytest.approx(6.0, abs=0.01)
        assert claude_outlier["delta"] == pytest.approx(-2.0, abs=0.01)
        assert claude_outlier["outlier_severity"] == "high"

    @pytest.mark.asyncio
    async def test_7_weighted_total_calculation(self):
        """#7: weighted_total 계산 (5 차원 × 가중치 = 100 검증)."""
        # 모든 dim 점수 8 → mean=8.0 → weighted_total = 8×100/10 = 80.0
        scores = {d: 8 for d in DIMENSIONS}
        panel = _build_panel({
            "gemini": make_success_fn(scores),
            "gpt": make_success_fn(scores),
            "claude": make_success_fn(scores),
        })
        result = await panel.evaluate(SAMPLE_HTML)

        assert result["aggregate"]["weighted_total"] == pytest.approx(80.0, abs=0.01)
        # 모든 점수 동일 → stdev 0
        for d in DIMENSIONS:
            assert result["aggregate"]["stdev_scores"][d] == 0.0
        # 가중치 합 = 100 인지 (TEST_CONFIG)
        assert sum(TEST_CONFIG["weights"].values()) == 100

    @pytest.mark.asyncio
    async def test_8_concurrent_faster_than_serial(self):
        """#8: 3 호출이 직렬보다 짧음 (asyncio.gather 동시성)."""
        scores = {d: 7 for d in DIMENSIONS}
        per_call_latency = 0.30  # 300ms
        panel = _build_panel({
            "gemini": make_success_fn(scores, latency=per_call_latency),
            "gpt": make_success_fn(scores, latency=per_call_latency),
            "claude": make_success_fn(scores, latency=per_call_latency),
        })
        started = time.monotonic()
        result = await panel.evaluate(SAMPLE_HTML)
        elapsed = time.monotonic() - started

        # 직렬 합 = 0.9s. 동시 호출 = ~0.3s. 충분한 마진:
        assert elapsed < per_call_latency * 2, (
            f"concurrent 호출이 직렬보다 의미있게 짧지 않음: {elapsed:.3f}s"
        )
        assert result["status"] == "completed"

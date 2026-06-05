"""Judge Panel 오케스트레이터 (Stage 4).

3-Model (Gemini + GPT + Claude) 가 ``asyncio.gather`` 로 동시 호출되어 콘텐츠를
독립적으로 평가하고, 평균/표준편차/outlier 를 집계해 ``judge_panel.json`` 으로 산출.

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md

테스트 가능성을 위해 3개 judge 함수는 모두 의존성 주입(DI). production 에서는
``from_settings`` 클래스 메서드로 자동 구성하고, 테스트에서는 mock async 함수
주입.
"""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from backend.core.judge_model_resolver import resolve_judge_model, validate_judge_weights

logger = logging.getLogger(__name__)

# Judge 함수 시그니처: keyword-only, async, 반환 dict
JudgeFn = Callable[..., Awaitable[dict[str, Any]]]

JUDGE_NAMES: tuple[str, ...] = ("gemini", "gpt", "claude")

# 호출당 토큰 추정치 (명세 비용 표 기반)
_TOKEN_ESTIMATE = {"input": 2000, "output": 1000}

# USD per 1M tokens (in, out) — 명세 표 추정값. 실측 시 settings 로 옮길 수도 있음.
_JUDGE_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (1.25, 5.00),
    "gpt-5": (5.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
}


def _estimate_call_cost(model_id: str) -> float:
    """단일 judge 호출 비용 추정 (USD)."""
    in_price, out_price = _JUDGE_PRICE_TABLE.get(model_id, (0.0, 0.0))
    return (
        _TOKEN_ESTIMATE["input"] / 1_000_000 * in_price
        + _TOKEN_ESTIMATE["output"] / 1_000_000 * out_price
    )


class JudgePanel:
    """3-Model Judge 오케스트레이터.

    Usage:
        # production
        panel = JudgePanel.from_settings(runtime_override=None)
        result = asyncio.run(panel.evaluate(input_html))

        # test (DI)
        panel = JudgePanel(
            config={"models": {...}, "weights": {...}, "budget_per_run_usd": 0.05},
            prompts={"gemini": "...", "gpt": "...", "claude": "..."},
            judge_fns={"gemini": mock_fn, "gpt": mock_fn, "claude": mock_fn},
            runtime_override=None,
        )
    """

    def __init__(
        self,
        *,
        config: dict[str, Any],
        prompts: dict[str, str],
        judge_fns: dict[str, JudgeFn],
        runtime_override: dict | None = None,
    ):
        """
        Args:
            config: ``judge_panel`` 섹션. 필수 키 ``models``, ``weights``.
                선택 ``budget_per_run_usd``, ``timeout_sec``.
            prompts: ``{"gemini": ..., "gpt": ..., "claude": ...}`` 시스템 프롬프트.
            judge_fns: 동일 키. async ``(*, model_id, system_prompt, user_prompt) -> dict``.
            runtime_override: 어드민 UI 런타임 override (B3-S3 hook).
        """
        self.config = config
        self.prompts = prompts
        self.judge_fns = judge_fns
        self.runtime_override = runtime_override

        # startup 검증: 가중치 합 100
        validate_judge_weights(config["weights"])

        for name in JUDGE_NAMES:
            if name not in prompts:
                raise ValueError(f"prompts['{name}'] 누락")
            if name not in judge_fns:
                raise ValueError(f"judge_fns['{name}'] 누락")

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    async def evaluate(self, input_html: str) -> dict[str, Any]:
        """3 judge 동시 호출 + 집계.

        Returns:
            judge_panel.json 스키마의 dict.
        """
        started = time.monotonic()

        # 모델 해석 (3단계 우선순위)
        models_used: dict[str, str] = {}
        models_resolution_source: dict[str, str] = {}
        for name in JUDGE_NAMES:
            model_id, source = resolve_judge_model(
                name,
                runtime_override=self.runtime_override,
                config_defaults=self.config["models"],
            )
            models_used[name] = model_id
            models_resolution_source[name] = source

        # 동시 호출
        tasks = [
            self._invoke_judge(name, models_used[name], input_html) for name in JUDGE_NAMES
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        evaluations: dict[str, dict[str, Any]] = {}
        failed_models: list[str] = []
        for name, result in zip(JUDGE_NAMES, results):
            if isinstance(result, BaseException):
                failed_models.append(name)
                logger.warning("Judge %s 실패: %s", name, result)
            else:
                evaluations[name] = result

        duration_ms = int((time.monotonic() - started) * 1000)
        input_size_bytes = len(input_html.encode("utf-8"))

        # 비용은 실제로 호출된 (성공·실패 무관) 모델 기준으로 추정
        cost_estimate = sum(_estimate_call_cost(models_used[n]) for n in JUDGE_NAMES)

        result: dict[str, Any] = {
            "stage": 4,
            "input_source": "final_output.html",
            "input_size_bytes": input_size_bytes,
            "models_used": models_used,
            "models_resolution_source": models_resolution_source,
            "evaluations": evaluations,
            "failed_models": failed_models,
            "duration_ms": duration_ms,
            "cost_usd_estimate": round(cost_estimate, 4),
        }

        if len(evaluations) == 0:
            result["status"] = "failed"
            result["aggregate"] = None
        else:
            result["aggregate"] = self._compute_aggregate(evaluations)
            result["status"] = "completed" if len(evaluations) == 3 else "degraded"

        return result

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------
    async def _invoke_judge(self, name: str, model_id: str, input_html: str) -> dict[str, Any]:
        timeout = float(self.config.get("timeout_sec", 60))
        coro = self.judge_fns[name](
            model_id=model_id,
            system_prompt=self.prompts[name],
            user_prompt=input_html,
        )
        return await asyncio.wait_for(coro, timeout=timeout)

    def _compute_aggregate(self, evaluations: dict[str, dict[str, Any]]) -> dict[str, Any]:
        weights: dict[str, float] = self.config["weights"]
        dimensions = list(weights.keys())

        mean_scores: dict[str, float] = {}
        stdev_scores: dict[str, float] = {}
        for dim in dimensions:
            vals = [
                ev["scores"][dim] for ev in evaluations.values()
                if isinstance(ev.get("scores"), dict) and dim in ev["scores"]
            ]
            if not vals:
                mean_scores[dim] = 0.0
                stdev_scores[dim] = 0.0
                continue
            m = statistics.fmean(vals)
            s = statistics.pstdev(vals) if len(vals) > 1 else 0.0
            mean_scores[dim] = round(m, 2)
            stdev_scores[dim] = round(s, 2)

        # weighted_total: sum(mean[dim] * weight[dim]) / 10
        # 가중치 합 100, 점수 1-10 → 결과 10-100 스케일
        weighted_total = round(
            sum(mean_scores[d] * weights[d] for d in dimensions) / 10, 1
        )

        # outliers: σ 가 의미 있을 만큼 크고 (>= 0.5) |delta| 가 severity threshold 이상.
        # 명세서가 적은 1.5σ 룰은 통계적 의도이나 N=3 분포에서는 거의 잡히지 않으므로
        # 명세 severity 표 (|delta| >= 1.0 → medium, >= 2.0 → high) 와 일관되도록
        # `|delta| >= 1.0` 을 outlier 판정 임계값으로 사용. 1.5σ 와 양립할 때는 둘 다 만족.
        outliers: list[dict[str, Any]] = []
        for dim in dimensions:
            vals_with_model = [
                (name, ev["scores"][dim])
                for name, ev in evaluations.items()
                if isinstance(ev.get("scores"), dict) and dim in ev["scores"]
            ]
            if len(vals_with_model) < 3:
                continue
            scores_only = [v for _, v in vals_with_model]
            m = statistics.fmean(scores_only)
            s = statistics.pstdev(scores_only)
            if s < 0.5:
                continue
            for name, score in vals_with_model:
                delta = score - m
                abs_delta = abs(delta)
                if abs_delta < 1.0:
                    continue  # low 미만은 outlier 아님
                if abs_delta >= 2.0:
                    severity = "high"
                else:
                    severity = "medium"
                outliers.append({
                    "dimension": dim,
                    "model": name,
                    "score": score,
                    "mean": round(m, 2),
                    "delta": round(delta, 2),
                    "outlier_severity": severity,
                })

        return {
            "mean_scores": mean_scores,
            "stdev_scores": stdev_scores,
            "weighted_total": weighted_total,
            "outliers": outliers,
        }

    # ------------------------------------------------------------------
    # 팩토리
    # ------------------------------------------------------------------
    @classmethod
    def from_settings(cls, *, runtime_override: dict | None = None) -> "JudgePanel":
        """config/agents.yaml + prompt 파일 + 기본 LLM 클라이언트로 자동 구성."""
        # lazy import (순환 의존 회피, 테스트에서 SDK 미설치 환경 보호)
        from backend.core.anthropic_client import call_anthropic_judge
        from backend.core.openai_client import call_openai_judge
        from backend.core.settings import load_judge_panel_config

        config = load_judge_panel_config()
        prompts = _load_judge_prompts()
        judge_fns: dict[str, JudgeFn] = {
            "gemini": _call_gemini_judge_default,
            "gpt": call_openai_judge,
            "claude": call_anthropic_judge,
        }
        return cls(
            config=config,
            prompts=prompts,
            judge_fns=judge_fns,
            runtime_override=runtime_override,
        )


# =====================================================================
# 프롬프트 로딩
# =====================================================================
_PROMPT_FILES = {
    "gemini": "10_judge_gemini.md",
    "gpt": "11_judge_gpt.md",
    "claude": "12_judge_claude.md",
}


def _load_judge_prompts() -> dict[str, str]:
    """backend/agents/prompts/{10,11,12}_judge_*.md 로드."""
    base = Path(__file__).resolve().parents[1] / "agents" / "prompts"
    out = {}
    for name, fname in _PROMPT_FILES.items():
        path = base / fname
        if not path.exists():
            raise FileNotFoundError(f"Judge 프롬프트 없음: {path}")
        out[name] = path.read_text(encoding="utf-8")
    return out


# =====================================================================
# Gemini async helper (judge_panel 내부 — 별도 모듈로 분리하지 않음)
# =====================================================================
async def _call_gemini_judge_default(
    *,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """Gemini async 호출 (google-genai aio)."""
    from google import genai
    from google.genai import types

    from backend.core.runtime_keys import get_provider_key
    from backend.core.settings import get_settings

    # B3-S3-E A2: 런타임 override > env. 클라이언트 초기화 인자(json mode) 변경 금지.
    api_key = get_provider_key("gemini") or get_settings().gemini_api_key
    client = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        system_instruction=system_prompt or None,
        response_mime_type="application/json",
    )

    response = await asyncio.wait_for(
        client.aio.models.generate_content(
            model=model_id,
            contents=user_prompt,
            config=config,
        ),
        timeout=timeout_sec,
    )

    content = response.text or ""
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Gemini 응답이 JSON object 가 아닙니다: type={type(parsed).__name__}"
        )
    return parsed

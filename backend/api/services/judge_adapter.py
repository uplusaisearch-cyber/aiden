"""judge_panel.json (Stage 4 raw) → JudgeResult (프론트 응답 스키마) 변환.

- per-model is_outlier: 5축 중 1개라도 |score - axis_mean| > 1.5 * axis_stdev
  (axis_stdev=0 또는 결측이면 그 축은 outlier 판정 제외).
- consensus_level:
    high  → max(axis_stdev) < 1.0
    medium → 1.0 <= max(axis_stdev) < 2.0
    low   → max(axis_stdev) >= 2.0
- comment: one_line_verdict + 강점 + 약점 을 한국어 한 줄로 합성 (200~500자 목표).
- aggregate_overall: 각 모델 overall_score 의 산술 평균.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.api.schemas.judge import (
    ConsensusLevel,
    CriterionScore,
    JudgeResult,
    ModelEvaluation,
)

AXES: tuple[str, ...] = (
    "topic_fit",
    "content_quality",
    "interactivity",
    "tone_authenticity",
    "timeliness_trust",
)

_MODEL_ORDER: tuple[str, ...] = ("gemini", "gpt", "claude")

# Outlier 임계치
_OUTLIER_SIGMA = 1.5

# Consensus 임계치
_CONSENSUS_HIGH_MAX_STDEV = 1.0
_CONSENSUS_MEDIUM_MAX_STDEV = 2.0


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _criterion_score_from(d: dict[str, Any]) -> CriterionScore:
    return CriterionScore(
        topic_fit=_to_float(d.get("topic_fit")),
        content_quality=_to_float(d.get("content_quality")),
        interactivity=_to_float(d.get("interactivity")),
        tone_authenticity=_to_float(d.get("tone_authenticity")),
        timeliness_trust=_to_float(d.get("timeliness_trust")),
    )


def _build_comment(ev: dict[str, Any]) -> str:
    verdict = (ev.get("one_line_verdict") or "").strip()
    strengths = [s for s in (ev.get("strengths") or []) if s]
    weaknesses = [w for w in (ev.get("weaknesses") or []) if w]
    parts: list[str] = []
    if verdict:
        parts.append(verdict)
    if strengths:
        parts.append("강점: " + " / ".join(strengths))
    if weaknesses:
        parts.append("약점: " + " / ".join(weaknesses))
    return " · ".join(parts)


def _detect_outlier(scores: dict[str, Any], mean_scores: dict[str, Any],
                    stdev_scores: dict[str, Any]) -> bool:
    for axis in AXES:
        s = scores.get(axis)
        m = mean_scores.get(axis)
        sd = stdev_scores.get(axis)
        if s is None or m is None or sd is None:
            continue
        sd_f = _to_float(sd)
        if sd_f <= 0:
            continue
        if abs(_to_float(s) - _to_float(m)) > _OUTLIER_SIGMA * sd_f:
            return True
    return False


def _consensus_level(stdev_scores: dict[str, Any]) -> ConsensusLevel:
    values = [
        _to_float(stdev_scores.get(axis))
        for axis in AXES
        if stdev_scores.get(axis) is not None
    ]
    if not values:
        return "high"
    max_sd = max(values)
    if max_sd < _CONSENSUS_HIGH_MAX_STDEV:
        return "high"
    if max_sd < _CONSENSUS_MEDIUM_MAX_STDEV:
        return "medium"
    return "low"


def adapt_judge_panel(raw: dict[str, Any], run_id: str) -> JudgeResult:
    """raw judge_panel.json dict → JudgeResult."""
    raw_evals: dict[str, Any] = raw.get("evaluations") or {}
    raw_agg: dict[str, Any] = raw.get("aggregate") or {}
    mean_scores: dict[str, Any] = raw_agg.get("mean_scores") or {}
    stdev_scores: dict[str, Any] = raw_agg.get("stdev_scores") or {}
    models_used: dict[str, Any] = raw.get("models_used") or {}

    evaluations: list[ModelEvaluation] = []
    for model_id in _MODEL_ORDER:
        ev = raw_evals.get(model_id)
        if not isinstance(ev, dict):
            continue
        scores = ev.get("scores") or {}
        evaluations.append(
            ModelEvaluation(
                model_id=model_id,
                model_name=str(ev.get("model") or models_used.get(model_id) or model_id),
                scores=_criterion_score_from(scores),
                overall=_to_float(ev.get("overall_score")),
                comment=_build_comment(ev),
                is_outlier=_detect_outlier(scores, mean_scores, stdev_scores),
            ),
        )

    aggregate = _criterion_score_from(mean_scores)
    overalls = [e.overall for e in evaluations]
    aggregate_overall = round(sum(overalls) / len(overalls), 2) if overalls else 0.0

    timestamp = str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat())

    return JudgeResult(
        run_id=run_id,
        evaluations=evaluations,
        aggregate=aggregate,
        aggregate_overall=aggregate_overall,
        consensus_level=_consensus_level(stdev_scores),
        timestamp=timestamp,
    )

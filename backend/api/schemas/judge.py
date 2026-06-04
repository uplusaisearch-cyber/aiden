"""Judge Panel 응답 스키마 (B3-S3-D).

기존 raw judge_panel.json (Stage 4 산출물) 을 프론트 시각화에 적합한 형태로 변환한
응답. 5축 dimension 명은 실측 judge_panel.json 구조(topic_fit / content_quality /
interactivity / tone_authenticity / timeliness_trust)를 그대로 사용 — 명세서가
지정한 fluffy 한 영문 키(factuality/novelty/clarity/completeness/interactivity)
대신 데이터 진실(소스 그대로) 우선.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# 5축 키 — 실측 judge_panel.json 의 dimension 명과 동일
AxisKey = Literal[
    "topic_fit",
    "content_quality",
    "interactivity",
    "tone_authenticity",
    "timeliness_trust",
]

ModelId = Literal["gemini", "gpt", "claude"]
ConsensusLevel = Literal["high", "medium", "low"]


class CriterionScore(BaseModel):
    """5축 점수 (0~10 스케일)."""

    topic_fit: float
    content_quality: float
    interactivity: float
    tone_authenticity: float
    timeliness_trust: float


class ModelEvaluation(BaseModel):
    model_id: ModelId
    model_name: str
    scores: CriterionScore
    overall: float
    comment: str
    is_outlier: bool


class JudgeResult(BaseModel):
    """프론트 Judge Panel 시각화 응답."""

    run_id: str
    evaluations: list[ModelEvaluation]
    aggregate: CriterionScore
    aggregate_overall: float
    consensus_level: ConsensusLevel
    timestamp: str

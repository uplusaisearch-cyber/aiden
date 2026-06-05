"""Admin API 스키마 (B3-S3-E).

- API 키 (방안 A — 런타임 메모리만)
- 발행 토픽 레지스트리 (Method A — data/topic_registry.json)
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------
KeyProvider = Literal["gemini", "openai", "anthropic"]
KeySource = Literal["runtime", "env", "none"]


class KeyStatus(BaseModel):
    provider: KeyProvider
    source: KeySource
    masked: str = ""              # "AIza…••••" — 평문 절대 금지


class KeyStatusListResponse(BaseModel):
    keys: list[KeyStatus]


class KeySetRequest(BaseModel):
    provider: KeyProvider
    # 평문 키 — 응답·로그에 절대 노출 금지
    key: str = Field(..., min_length=1)


class KeySetResponse(BaseModel):
    provider: KeyProvider
    source: KeySource             # 설정 후 = "runtime"
    masked: str


class KeyClearResponse(BaseModel):
    provider: KeyProvider
    cleared: bool                 # True = override 가 있었고 제거됨
    source: KeySource             # 제거 후 = "env" 또는 "none"
    masked: str


# ---------------------------------------------------------------------
# Topic Registry
# ---------------------------------------------------------------------
# 명세 §A3 의 category 는 generate enum 과 다를 수 있으므로,
# 레지스트리 자체 카테고리는 광역 자유 입력으로 두되 권장 값을 화이트리스트로 노출.
# RESULT.md 에 결정사항 기록 — generate enum 과 매핑하지 않고 자체 스키마 사용.
TopicCategory = Literal["food", "ai_trend", "safety", "culture", "free"]
TopicStatus = Literal["published", "rejected", "expired"]


class TopicEntry(BaseModel):
    id: str
    topic: str
    category: TopicCategory
    status: TopicStatus
    published_at: str             # ISO8601
    expiry: str | None = None
    rejected_similar_to: str | None = None
    created_at: str               # ISO8601
    updated_at: str               # ISO8601


class TopicCreateRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200)
    category: TopicCategory
    status: TopicStatus = "published"
    expiry: str | None = None      # ISO8601
    rejected_similar_to: str | None = None


class TopicUpdateRequest(BaseModel):
    status: TopicStatus | None = None
    expiry: str | None = None
    rejected_similar_to: str | None = None


class TopicListResponse(BaseModel):
    topics: list[TopicEntry]
    total: int


class TopicDeleteResponse(BaseModel):
    id: str
    deleted: bool

"""``/api/admin/registry`` — 발행 토픽 레지스트리 CRUD (Method A)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.api.schemas.admin import (
    TopicCreateRequest,
    TopicDeleteResponse,
    TopicEntry,
    TopicListResponse,
    TopicUpdateRequest,
)
from backend.api.services.topic_registry import TopicRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/registry", tags=["admin-registry"])


def _to_entry(raw: dict) -> TopicEntry:
    return TopicEntry(**raw)


@router.get("", response_model=TopicListResponse)
def list_topics(status: str | None = None, category: str | None = None) -> TopicListResponse:
    items = TopicRegistry.instance().list(status=status, category=category)
    return TopicListResponse(
        topics=[_to_entry(i) for i in items],
        total=len(items),
    )


@router.post("", response_model=TopicEntry, status_code=201)
def create_topic(body: TopicCreateRequest) -> TopicEntry:
    try:
        entry = TopicRegistry.instance().create(
            topic=body.topic,
            category=body.category,
            status=body.status,
            expiry=body.expiry,
            rejected_similar_to=body.rejected_similar_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_entry(entry)


@router.patch("/{item_id}", response_model=TopicEntry)
def update_topic(item_id: str, body: TopicUpdateRequest) -> TopicEntry:
    try:
        updated = TopicRegistry.instance().update(
            item_id,
            status=body.status,
            expiry=body.expiry,
            rejected_similar_to=body.rejected_similar_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail=f"topic not found: {item_id}")
    return _to_entry(updated)


@router.delete("/{item_id}", response_model=TopicDeleteResponse)
def delete_topic(item_id: str) -> TopicDeleteResponse:
    deleted = TopicRegistry.instance().delete(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"topic not found: {item_id}")
    return TopicDeleteResponse(id=item_id, deleted=True)

"""``/api/admin/keys`` — 런타임 API 키 관리 (방안 A).

- 평문 키 응답·로그 노출 금지 (KeySetRequest body 만 입력으로 받음)
- 재시작/재배포 시 소실 — env 로 fallback. UI 안내 필수.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from backend.api.schemas.admin import (
    KeyClearResponse,
    KeySetRequest,
    KeySetResponse,
    KeyStatus,
    KeyStatusListResponse,
)
from backend.core.runtime_keys import SUPPORTED_PROVIDERS, RuntimeKeyStore, mask

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/keys", tags=["admin-keys"])


def _status_payload(provider: str) -> KeyStatus:
    resolution = RuntimeKeyStore.instance().resolve(provider)
    return KeyStatus(
        provider=provider,  # type: ignore[arg-type]
        source=resolution.source,
        masked=mask(resolution.key),
    )


@router.get("", response_model=KeyStatusListResponse)
def list_keys() -> KeyStatusListResponse:
    return KeyStatusListResponse(
        keys=[_status_payload(p) for p in SUPPORTED_PROVIDERS]
    )


@router.put("", response_model=KeySetResponse)
def set_key(body: KeySetRequest) -> KeySetResponse:
    store = RuntimeKeyStore.instance()
    try:
        store.set(body.provider, body.key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    resolution = store.resolve(body.provider)
    # ⚠️ resolution.key 는 평문 — masked 만 응답에 사용.
    return KeySetResponse(
        provider=body.provider,
        source=resolution.source,
        masked=mask(resolution.key),
    )


@router.delete("/{provider}", response_model=KeyClearResponse)
def clear_key(provider: str) -> KeyClearResponse:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=f"unsupported provider: {provider}",
        )
    store = RuntimeKeyStore.instance()
    existed = store.clear(provider)
    resolution = store.resolve(provider)
    return KeyClearResponse(
        provider=provider,  # type: ignore[arg-type]
        cleared=existed,
        source=resolution.source,
        masked=mask(resolution.key),
    )

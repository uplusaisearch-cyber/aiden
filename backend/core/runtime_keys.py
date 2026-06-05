"""런타임 API 키 저장소 (방안 A).

명세: docs/patches/2026-06-04_b3-s3-e_admin_persona_ops.md §A2

- 프로세스 전역 메모리 dict. 파일/DB/외부 스토리지 없음.
- 우선순위: runtime override > env (Settings 의 *_api_key)
- 재시작·재배포 시 소실 (의도). UI 안내 + RESULT.md 명시.
- 평문 키를 로그·응답에 노출 금지 → ``mask()`` 만 외부 노출.
- 클라이언트 SDK 초기화 인자(grounding/response_mime_type) 는 절대 변경하지 말 것.
  여기는 "키 조회" 만 책임진다.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# 화이트리스트 — admin 라우터에서 provider 검증에 재사용한다.
SUPPORTED_PROVIDERS: tuple[str, ...] = ("gemini", "openai", "anthropic")

# Settings 필드와의 대응. env 키 조회는 항상 Settings 경유.
_SETTINGS_FIELD: dict[str, str] = {
    "gemini": "gemini_api_key",
    "openai": "openai_api_key",
    "anthropic": "anthropic_api_key",
}


KeySource = Literal["runtime", "env", "none"]


@dataclass(frozen=True)
class KeyResolution:
    provider: str
    key: str           # 평문 — **로그·응답 노출 금지**
    source: KeySource

    @property
    def is_set(self) -> bool:
        return bool(self.key)


class RuntimeKeyStore:
    """프로세스 싱글톤. ``threading.Lock`` 으로 동시성 보호.

    `set(provider, key)` / `clear(provider)` / `get(provider)` 만 노출.
    Settings 가 깨지더라도 env fallback 으로 graceful 처리.
    """

    _instance: "RuntimeKeyStore | None" = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._overrides: dict[str, str] = {}
        self._lock = threading.Lock()

    @classmethod
    def instance(cls) -> "RuntimeKeyStore":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def set(self, provider: str, key: str) -> None:
        provider = _validate_provider(provider)
        if not key or not key.strip():
            raise ValueError("빈 키는 허용되지 않습니다.")
        with self._lock:
            self._overrides[provider] = key.strip()
        # ⚠️ 키 본문을 로그에 절대 출력하지 말 것. 길이만 기록.
        logger.info("runtime key set: provider=%s length=%d", provider, len(key))

    def clear(self, provider: str) -> bool:
        provider = _validate_provider(provider)
        with self._lock:
            existed = self._overrides.pop(provider, None) is not None
        if existed:
            logger.info("runtime key cleared: provider=%s", provider)
        return existed

    def resolve(self, provider: str) -> KeyResolution:
        """provider 의 ‘조회 시점’ 키와 출처를 반환.

        - runtime override 가 있으면 그것을 우선
        - 없으면 Settings (env) 값을 반환
        - 둘 다 없으면 빈 문자열 + source=none
        """
        provider = _validate_provider(provider)
        with self._lock:
            override = self._overrides.get(provider)
        if override:
            return KeyResolution(provider=provider, key=override, source="runtime")

        env_key = _read_env_key(provider)
        if env_key:
            return KeyResolution(provider=provider, key=env_key, source="env")
        return KeyResolution(provider=provider, key="", source="none")

    def has_runtime_override(self, provider: str) -> bool:
        provider = _validate_provider(provider)
        with self._lock:
            return provider in self._overrides

    def snapshot(self) -> dict[str, KeyResolution]:
        """전체 provider 의 현재 해석 결과를 반환 (admin API 용)."""
        return {p: self.resolve(p) for p in SUPPORTED_PROVIDERS}


# =====================================================================
# 모듈 헬퍼 — 클라이언트 코드에서 가져다 쓸 진입점
# =====================================================================
def get_provider_key(provider: str) -> str:
    """현재 시점의 키만 반환 (출처 무관). 클라이언트가 평문으로 받아 SDK 에 전달.

    빈 문자열 가능 (env/override 둘 다 비었을 때) — 호출 측에서 누락 처리.
    """
    return RuntimeKeyStore.instance().resolve(provider).key


def mask(key: str, *, head: int = 4) -> str:
    """``AIza…••••`` 형식의 마스킹. 빈 문자열은 그대로 빈 문자열."""
    if not key:
        return ""
    head_part = key[:head]
    return f"{head_part}…••••"


# =====================================================================
# 내부 헬퍼
# =====================================================================
def _validate_provider(provider: str) -> str:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"unsupported provider: {provider!r}. "
            f"허용: {SUPPORTED_PROVIDERS}"
        )
    return provider


def _read_env_key(provider: str) -> str:
    """Settings 경유로 env 값을 읽는다. Settings 자체가 깨지면 빈 문자열."""
    field = _SETTINGS_FIELD[provider]
    try:
        # 늦은 import — 모듈 import 순환 회피
        from backend.core.settings import get_settings

        settings = get_settings()
        value = getattr(settings, field, "") or ""
        return value
    except Exception as exc:  # noqa: BLE001
        # Settings 실패는 healthcheck 등이 다루므로 여기선 조용히 빈 키.
        logger.debug("env 키 로드 실패 (provider=%s): %s", provider, exc)
        return ""

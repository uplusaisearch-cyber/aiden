"""Anthropic API 클라이언트 (Newsroom Writer/Editor 용).

GeminiClient 와 동일한 ``.call(system_prompt, user_input, use_grounding=, temperature=) -> dict``
시그니처를 노출 → ``concrete_agents.make_agent_callable`` 이 LLM provider 무관하게
호출 가능. Provider 교체는 ``_build_client_for_alias`` 의 분기 한 곳에서만 처리.

명세: docs/patches/B4-S2-writer-editor-claude.md (Commit 1)

핵심 차이 (vs GeminiClient):
- Anthropic SDK 는 native JSON mode 미지원 → system prompt 에 JSON 강제 hint 추가
- Claude 가 ``` json 코드펜스 자주 붙임 → 응답에서 _strip_code_fence 로 제거
- Grounding(google_search) 미지원 → use_grounding=True 면 warning 만 남기고 무시
  (grounding 의존 agent 의 anthropic_* alias 사용은 호출자가 ``_build_agents`` 에서 차단)

재시도 정책: GeminiClient 와 유사 (503/429/오버로드 retryable, 4xx 즉시 실패).
"""
from __future__ import annotations

import json
import logging
import os
import random
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# 기본 모델 — Commit 2 에서 yaml writer/editor 매핑이 별칭을 통해 실모델 ID 주입.
# 본 클라이언트 단독 사용 시(yaml override 없음) 의 안전 디폴트.
DEFAULT_MODEL = "claude-opus-4-7"

# 재시도 정책 (GeminiClient 와 동일 형식)
_MAX_RETRIES = 3              # 첫 시도 + 재시도 2회
_BASE_BACKOFF_SEC = 1.0       # 1s → 2s → 4s → 8s
_BACKOFF_CAP_SEC = 8.0
_JITTER_RATIO = 0.3

_JSON_FORCE_HINT = (
    "\n\n출력 형식: 반드시 단일 JSON 객체만 반환하세요. "
    "코드블록(```)이나 JSON 외 텍스트(설명·주석·요약 등)는 절대 포함하지 마세요. "
    "응답의 첫 글자는 `{`, 마지막 글자는 `}` 여야 합니다."
)


class AnthropicEmptyResponseError(RuntimeError):
    """Claude 응답 content 가 비어 있는 케이스. retryable 분류."""


def _is_retryable(exc: BaseException) -> bool:
    """503/429/5xx + 빈 응답 retryable, 명백한 4xx 즉시 실패."""
    if isinstance(exc, AnthropicEmptyResponseError):
        return True
    msg = str(exc)
    name = type(exc).__name__
    non_retryable_markers = (
        "400 ", "400:", "401 ", "401:", "403 ", "403:", "404 ", "404:",
        "invalid_request", "authentication", "permission_error", "not_found",
        "BadRequestError", "AuthenticationError", "PermissionDeniedError", "NotFoundError",
    )
    for m in non_retryable_markers:
        if m in msg or m in name:
            return False
    retryable_markers = (
        "429", "rate_limit", "RateLimitError",
        "529", "overloaded", "OverloadedError",
        "500", "502", "503", "504",
        "InternalServerError", "APIConnectionError", "APITimeoutError",
        "ServiceUnavailable",
    )
    for m in retryable_markers:
        if m in msg or m in name:
            return True
    return False


def _sleep_with_backoff(attempt_no: int) -> None:
    base = min(_BASE_BACKOFF_SEC * (2 ** attempt_no), _BACKOFF_CAP_SEC)
    jitter = base * _JITTER_RATIO
    delay = max(0.1, base + random.uniform(-jitter, jitter))
    time.sleep(delay)


class AnthropicAgentClient:
    """Anthropic API wrapper. GeminiClient 와 동일 interface.

    Usage:
        client = AnthropicAgentClient(api_key="...", model="claude-sonnet-4-6")
        result = client.call(
            system_prompt="...",
            user_input={"category": "맛집"},
            use_grounding=False,
        )

    제약:
        - ``use_grounding=True`` 는 무시 (Anthropic 미지원). warning 로그만 남김.
        - 호출자(``_build_agents``)에서 grounding 의존 에이전트에 anthropic_* alias 매핑되지
          않도록 사전 차단해야 한다 (가드는 호출자 책임).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        models: list[str] | None = None,
        max_retries: int = _MAX_RETRIES,
    ):
        # 늦은 import — anthropic SDK 미설치 환경에서도 모듈 import 자체는 가능.
        try:
            from anthropic import Anthropic  # noqa: F401
        except ImportError as e:
            raise RuntimeError(
                "anthropic SDK 미설치. pip install anthropic 필요."
            ) from e

        # 키 우선순위: 인자 > 런타임 override > env. GeminiClient 의 dotenv fallback
        # 패턴 유사하게 처리.
        self.api_key = api_key
        if not self.api_key:
            try:
                from backend.core.runtime_keys import get_provider_key
                from backend.core.settings import get_settings
                self.api_key = get_provider_key("anthropic") or get_settings().anthropic_api_key
            except Exception:  # noqa: BLE001
                self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY 미설정. .env 또는 어드민 키 페이지에서 설정 필요."
            )

        # 모델 체인 결정: models > model > DEFAULT
        if models:
            chain = [m for m in models if m]
        elif model:
            chain = [model]
        else:
            chain = [DEFAULT_MODEL]
        if not chain:
            chain = [DEFAULT_MODEL]

        self.models: list[str] = chain
        self.model_name: str = chain[0]   # GeminiClient 호환 — B4-S1 라벨 메커니즘
        self.last_used_model: str | None = None
        self.max_retries = max_retries

    def call(
        self,
        system_prompt: str,
        user_input: dict,
        use_grounding: bool = False,
        temperature: float = 0.7,
    ) -> dict:
        """Anthropic 호출 후 JSON dict 반환.

        Args:
            system_prompt: 에이전트 system prompt (PromptLoader 로 로드된).
            user_input: 에이전트 입력 dict.
            use_grounding: Anthropic 미지원 — True 면 warning 만 남기고 무시.
            temperature: GeminiClient 호환 시그니처용. **SDK 에는 전달하지 않음** —
                claude-opus-4-7 등 신모델이 temperature 를 deprecated 처리하므로
                옵션 A (모든 호출에서 미전달, SDK 디폴트 사용) 적용. top_p/top_k 도
                wrapper 가 애초에 SDK 에 전달하지 않으므로 변경 불필요.

        Returns:
            파싱된 JSON dict.

        Raises:
            ValueError: JSON 파싱 실패 (재시도 X).
            RuntimeError: 재시도 모두 실패.
        """
        _ = temperature  # 인자 수신만, SDK 미전달 (deprecation 회피)

        if use_grounding:
            logger.warning(
                "AnthropicAgentClient: use_grounding=True 는 미지원 (Claude 는 google_search 없음). "
                "무시하고 호출 — grounding 의존 에이전트의 매핑 점검 필요.",
            )

        user_message = (
            "다음 JSON 입력을 받아 system prompt 의 출력 형식에 정확히 맞는 JSON 만 반환해주세요.\n\n"
            f"입력:\n```json\n{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```"
        )
        effective_system = (system_prompt or "") + _JSON_FORCE_HINT

        last_exc: BaseException | None = None
        total_models = len(self.models)

        for model_idx, model_name in enumerate(self.models):
            for attempt_no in range(self.max_retries):
                try:
                    raw = self._invoke(
                        model_name=model_name,
                        system=effective_system,
                        user_message=user_message,
                    )
                    cleaned = self._strip_code_fence(raw)
                    parsed = self._parse_json(cleaned)
                    self.last_used_model = model_name
                    self.model_name = model_name
                    if model_idx > 0 or attempt_no > 0:
                        logger.info(
                            "Anthropic 호출 성공 (model=%s, attempt=%d, model_idx=%d/%d)",
                            model_name, attempt_no + 1, model_idx + 1, total_models,
                        )
                    return parsed
                except ValueError:
                    # JSON 파싱 실패는 재시도 안 함 (모델 응답은 도착함)
                    raise
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    retryable = _is_retryable(exc)
                    is_last_attempt = attempt_no == self.max_retries - 1
                    is_last_model = model_idx == total_models - 1

                    if not retryable:
                        logger.error(
                            "Anthropic 호출 실패 (non-retryable, model=%s): %s",
                            model_name, exc,
                        )
                        raise

                    if is_last_attempt and is_last_model:
                        logger.error(
                            "Anthropic 호출 모든 폴백 소진 (model=%s, attempt=%d): %s",
                            model_name, attempt_no + 1, exc,
                        )
                        raise

                    if is_last_attempt:
                        next_model = self.models[model_idx + 1]
                        logger.warning(
                            "Anthropic %s 재시도 한계 도달 → 폴백: %s",
                            model_name, next_model,
                        )
                        break

                    logger.warning(
                        "Anthropic 호출 실패, 재시도 예정 (model=%s, attempt=%d/%d): %s",
                        model_name, attempt_no + 1, self.max_retries, exc,
                    )
                    _sleep_with_backoff(attempt_no)

        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Anthropic call failed for unknown reason")

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    def _invoke(
        self,
        *,
        model_name: str,
        system: str,
        user_message: str,
    ) -> str:
        """단일 모델 1회 호출. 재시도 없음.

        sampling 인자 (temperature/top_p/top_k) 는 SDK 에 전달하지 않음 — claude-opus-4-7
        등 신모델이 temperature 를 deprecated 처리. SDK 디폴트 사용으로 미래호환 확보.
        top_p/top_k 는 wrapper 가 애초에 미전달이라 변경 불필요.
        """
        from anthropic import Anthropic

        client = Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=model_name,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        content_parts = [b.text for b in response.content if hasattr(b, "text")]
        text = "".join(content_parts).strip()
        if not text:
            raise AnthropicEmptyResponseError(
                f"Empty response from Anthropic (model={model_name}, "
                f"stop_reason={getattr(response, 'stop_reason', None)})"
            )
        return text

    # _strip_code_fence: anthropic_client.py 의 동명 함수와 동일 동작.
    # 의도적 인라인 — judge 측 함수의 미세 변경이 newsroom 으로 새지 않도록 격리.
    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Claude 가 ```json ... ``` 펜스를 붙이면 제거."""
        s = text.strip()
        if s.startswith("```"):
            lines = s.split("\n", 1)
            s = lines[1] if len(lines) > 1 else ""
            if s.rstrip().endswith("```"):
                s = s.rstrip()[:-3]
        return s.strip()

    @staticmethod
    def _parse_json(text: str) -> dict:
        """응답을 JSON dict 로 파싱. Gemini 와 동일한 fallback 패턴."""
        text = text.strip()
        # 코드블록 한 번 더 (펜스 strip 이후에도 중첩 가능성)
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            logger.error("Anthropic JSON parse failed. Raw text head: %s", text[:300])
            raise ValueError(f"Failed to parse Anthropic response as JSON: {e}")

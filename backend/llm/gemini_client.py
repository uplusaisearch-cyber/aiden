"""Gemini API 클라이언트 (google-genai 신규 SDK).

목적: system_prompt + user_input(dict) → JSON dict 반환.
Grounding 옵션 지원 (Trend Scout / Fact-Checker 용).

⚠️ 제약: Gemini API 는 tools(Grounding) + ``response_mime_type='application/json'``
   동시 미지원. Grounding 사용 시 mime_type 안 쓰고 prompt 기반 JSON 강제 (옵션 B).

503/429 회복:
   - exponential backoff (1s → 2s → 4s → 8s, jitter ±30%)
   - 동일 모델 max_retries 도달 시 다음 모델로 폴백 (예: gemini-2.5-flash → gemini-2.5-flash-lite)
   - 4xx / JSON 파싱 실패 / 그 외 에러는 즉시 실패 (재시도/폴백 안 함)
   - 모델 리스트는 ``AIDEN_GEMINI_MODELS`` 환경변수 (콤마 구분) 또는 ``models=`` 인자로 제어
   - 마감 후 환경변수 한 줄 (단일 모델) 로 폴백 비활성화 가능

의존: ``google-genai`` (구 ``google-generativeai`` 와 다름)
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

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    logger.warning("google-genai 미설치. pip install google-genai")


# 기본 모델 체인 (2026-06 기준)
# - primary: gemini-2.5-flash
# - fallback: gemini-2.5-flash-lite (503 만성 시 안전판)
DEFAULT_MODELS: list[str] = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
DEFAULT_MODEL = DEFAULT_MODELS[0]

# 재시도 정책
_MAX_RETRIES_PER_MODEL = 3   # 모델당 시도 횟수 (첫 시도 + 재시도 2회)
_BASE_BACKOFF_SEC = 1.0      # 1s → 2s → 4s → 8s
_BACKOFF_CAP_SEC = 8.0
_JITTER_RATIO = 0.3

# Grounding 미지원 모델 (호출 시 자동으로 use_grounding=False 로 강등)
# - gemini-2.5-flash-lite 는 Google Search 도구 미지원 (공식 docs 기준).
# - 잘못된 경우 빈 set 으로 두면 강등 안 함.
_NO_GROUNDING_MODELS: set[str] = {"gemini-2.5-flash-lite"}

# Grounding 사용 시 JSON 강제용 추가 지시 (response_mime_type 못 박을 때)
JSON_FORCE_SUFFIX = (
    "\n\n출력 형식: 반드시 단일 JSON 객체만 반환하세요. "
    "코드블록(```)이나 JSON 외 텍스트(설명·주석·요약 등)는 절대 포함하지 마세요. "
    "응답의 첫 글자는 `{`, 마지막 글자는 `}` 여야 합니다."
)


class GeminiEmptyResponseError(RuntimeError):
    """Gemini 응답에 text 가 비어 있는 케이스.

    ``response.candidates[0].content == None`` (safety 차단 / 빈 응답 / finish_reason
    이 STOP 외 값) 등에서 발생. retryable 로 분류돼 다음 attempt / 다음 모델로 폴백.
    """


def _parse_models_env() -> list[str] | None:
    """``AIDEN_GEMINI_MODELS=a,b,c`` 환경변수 파싱."""
    raw = os.environ.get("AIDEN_GEMINI_MODELS", "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts or None


def _is_retryable_error(exc: BaseException) -> bool:
    """503 / 429 / 5xx + 빈 응답을 retryable 로 판정.

    google-genai SDK 의 에러 클래스가 버전마다 달라 message + class name 으로 판정.
    명백한 4xx (400/401/403/404) 는 즉시 실패.
    """
    # 빈 응답 (safety 차단 / candidate 없음) — 같은 모델 재시도 + 다음 모델 폴백 가치 있음
    if isinstance(exc, GeminiEmptyResponseError):
        return True

    msg = str(exc)
    name = type(exc).__name__

    # 명시적 비-재시도 신호 우선 (4xx)
    non_retryable_markers = (
        "400 ", "400:", "401 ", "401:", "403 ", "403:", "404 ", "404:",
        "INVALID_ARGUMENT", "UNAUTHENTICATED", "PERMISSION_DENIED", "NOT_FOUND",
    )
    for m in non_retryable_markers:
        if m in msg:
            return False

    # 재시도 가능 마커 (5xx + 429)
    retryable_markers = (
        "503", "UNAVAILABLE",
        "429", "RESOURCE_EXHAUSTED", "QUOTA_EXCEEDED",
        "500", "INTERNAL",
        "502", "BAD_GATEWAY",
        "504", "DEADLINE_EXCEEDED",
        "ServerError", "ServiceUnavailable",
    )
    for m in retryable_markers:
        if m in msg or m in name:
            return True

    # SDK 의 ServerError / APIError 류 (보수적 — 알 수 없는 에러는 retry 안 함)
    return False


def _sleep_with_backoff(attempt_no: int) -> None:
    """attempt_no=0 → 1s, 1 → 2s, 2 → 4s, 3 → 8s (±30% jitter, cap 8s)."""
    base = min(_BASE_BACKOFF_SEC * (2 ** attempt_no), _BACKOFF_CAP_SEC)
    jitter = base * _JITTER_RATIO
    delay = base + random.uniform(-jitter, jitter)
    delay = max(0.1, delay)
    time.sleep(delay)


class GeminiClient:
    """google-genai 기반 Gemini API wrapper.

    Usage:
        client = GeminiClient(api_key="...", model="gemini-2.5-flash")
        # 또는 폴백 체인 명시:
        client = GeminiClient(models=["gemini-2.5-flash", "gemini-2.5-flash-lite"])

        result_dict = client.call(
            system_prompt="...",
            user_input={"category": "맛집"},
            use_grounding=True,
        )

    제약:
        - ``use_grounding=True`` 일 때 ``response_mime_type='application/json'`` 사용 불가
          → prompt 에 JSON_FORCE_SUFFIX 추가하여 텍스트 모드에서 JSON 강제
        - ``use_grounding=False`` 일 때 ``response_mime_type='application/json'`` 사용
        - Grounding 미지원 모델로 폴백되면 자동으로 grounding off + JSON mode 로 강등
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        models: list[str] | None = None,
    ):
        if genai is None:
            raise RuntimeError("google-genai package not installed")

        # GOOGLE_AI_STUDIO_API_KEY (기존) 또는 GEMINI_API_KEY/GOOGLE_API_KEY (SDK 기본) 모두 지원
        self.api_key = (
            api_key
            or os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            # 엔트리포인트가 load_dotenv 를 호출하지 않은 경우 대비한 fallback.
            try:
                from dotenv import load_dotenv
                from pathlib import Path as _Path
                _root = _Path(__file__).resolve().parents[2]
                load_dotenv(dotenv_path=_root / ".env")
            except Exception:  # noqa: BLE001
                pass
            self.api_key = (
                os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY")
            )
        if not self.api_key:
            raise ValueError(
                "API 키 미설정. .env 에 GOOGLE_AI_STUDIO_API_KEY 또는 GEMINI_API_KEY 설정 필요."
            )

        # 모델 체인 결정: 우선순위 = models 인자 > model 인자 > env > default
        chain: list[str]
        if models:
            chain = [m for m in models if m]
        elif model:
            chain = [model]
        else:
            env_chain = _parse_models_env()
            chain = env_chain if env_chain else list(DEFAULT_MODELS)
        if not chain:
            chain = list(DEFAULT_MODELS)

        self.models: list[str] = chain
        self.model_name: str = chain[0]   # 외부 호환 (호출 후에는 last_used_model 우선)
        self.last_used_model: str | None = None

        self.client = genai.Client(api_key=self.api_key)

    def call(
        self,
        system_prompt: str,
        user_input: dict,
        use_grounding: bool = False,
        temperature: float = 0.7,
    ) -> dict:
        """Gemini 호출 후 JSON dict 반환.

        모델 체인을 순회하며, 모델당 ``_MAX_RETRIES_PER_MODEL`` 회 시도.
        503/429 등 retryable 에러만 재시도 + exponential backoff.

        Args:
            system_prompt: 에이전트 system prompt (PromptLoader 로 로드된).
            user_input: 에이전트 입력 dict.
            use_grounding: Google Search Grounding 사용 여부.
            temperature: 생성 temperature.

        Returns:
            파싱된 JSON dict.

        Raises:
            모든 모델 / 모든 retry 가 실패한 마지막 예외를 전파.
            JSON 파싱 실패 시 ValueError 즉시 전파 (재시도 X).
        """
        user_message = (
            "다음 JSON 입력을 받아 system prompt의 출력 형식에 정확히 맞는 JSON만 반환해주세요.\n\n"
            f"입력:\n```json\n{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```"
        )

        last_exc: BaseException | None = None
        total_models = len(self.models)

        for model_idx, model_name in enumerate(self.models):
            # Grounding 미지원 모델로 폴백되면 자동으로 grounding off
            effective_grounding = use_grounding and (model_name not in _NO_GROUNDING_MODELS)
            if use_grounding and not effective_grounding:
                logger.warning(
                    "모델 %s 는 Grounding 미지원 → use_grounding=False 로 강등 후 호출",
                    model_name,
                )

            for attempt_no in range(_MAX_RETRIES_PER_MODEL):
                try:
                    response = self._invoke(
                        model_name=model_name,
                        system_prompt=system_prompt,
                        user_message=user_message,
                        use_grounding=effective_grounding,
                        temperature=temperature,
                    )
                    raw_text = self._extract_text(response)
                    parsed = self._parse_json(raw_text)
                    # 성공 — 사용한 모델 기록
                    self.last_used_model = model_name
                    self.model_name = model_name
                    if model_idx > 0 or attempt_no > 0:
                        logger.info(
                            "Gemini 호출 성공 (model=%s, attempt=%d, model_idx=%d/%d)",
                            model_name, attempt_no + 1, model_idx + 1, total_models,
                        )
                    return parsed
                except ValueError:
                    # JSON 파싱 실패는 retry 안 함 (모델이 응답은 했음)
                    raise
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    retryable = _is_retryable_error(exc)
                    is_last_attempt = attempt_no == _MAX_RETRIES_PER_MODEL - 1
                    is_last_model = model_idx == total_models - 1

                    if not retryable:
                        logger.error(
                            "Gemini 호출 실패 (non-retryable, model=%s): %s",
                            model_name, exc,
                        )
                        raise

                    if is_last_attempt and is_last_model:
                        logger.error(
                            "Gemini 호출 모든 폴백 소진 (model=%s, attempt=%d): %s",
                            model_name, attempt_no + 1, exc,
                        )
                        raise

                    if is_last_attempt:
                        # 다음 모델로 폴백
                        next_model = self.models[model_idx + 1]
                        logger.warning(
                            "Gemini %s 재시도 한계 도달 → 폴백: %s (다음 모델)",
                            model_name, next_model,
                        )
                        break
                    # 동일 모델로 retry + backoff
                    logger.warning(
                        "Gemini 호출 실패, 재시도 예정 (model=%s, attempt=%d/%d): %s",
                        model_name, attempt_no + 1, _MAX_RETRIES_PER_MODEL, exc,
                    )
                    _sleep_with_backoff(attempt_no)

        # 안전망 — 정상 흐름에선 도달 안 함
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Gemini call failed for unknown reason")

    def _invoke(
        self,
        *,
        model_name: str,
        system_prompt: str,
        user_message: str,
        use_grounding: bool,
        temperature: float,
    ) -> Any:
        """단일 모델에 대해 generate_content 1회 호출 (재시도 없음)."""
        effective_system_prompt = system_prompt
        if use_grounding:
            effective_system_prompt = system_prompt + JSON_FORCE_SUFFIX

        config_kwargs: dict[str, Any] = {
            "system_instruction": effective_system_prompt,
            "temperature": temperature,
        }
        if use_grounding:
            config_kwargs["tools"] = [
                types.Tool(google_search=types.GoogleSearch())
            ]
        else:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)
        return self.client.models.generate_content(
            model=model_name,
            contents=user_message,
            config=config,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """response 객체에서 text 추출. Grounding 시 candidates 구조가 다를 수 있음.

        text 가 비어 있으면 ``GeminiEmptyResponseError`` raise (retryable).
        진단을 돕기 위해 finish_reason / block_reason 을 메시지에 포함.
        """
        # 1순위: response.text (대부분 케이스)
        text = getattr(response, "text", None)
        if text:
            return text

        # 2순위: candidates[0].content.parts[*].text 합치기.
        # content == None (safety 차단 / 빈 응답) 케이스를 명시적으로 분기.
        candidates = getattr(response, "candidates", None) or []
        finish_reason = None
        if candidates:
            cand = candidates[0]
            finish_reason = getattr(cand, "finish_reason", None)
            content = getattr(cand, "content", None)
            if content is not None:
                parts = getattr(content, "parts", None) or []
                texts = [getattr(p, "text", "") for p in parts]
                joined = "".join(t for t in texts if t)
                if joined:
                    return joined

        # 빈 응답 — retryable 예외 raise
        prompt_feedback = getattr(response, "prompt_feedback", None)
        block_reason = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None
        raise GeminiEmptyResponseError(
            f"Empty response from Gemini (finish_reason={finish_reason}, "
            f"block_reason={block_reason}, candidates={len(candidates)})"
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Gemini 응답에서 JSON 추출.

        ``` ```json ... ``` ``` 코드블록 또는 raw JSON 처리.
        """
        text = text.strip()

        # 코드블록 제거
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # JSON 추출 한 번 더 시도: 첫 { 와 마지막 } 사이
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass

            logger.error(f"JSON parse failed. Raw text head: {text[:300]}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}")

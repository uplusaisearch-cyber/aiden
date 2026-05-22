"""LLM 통합 wrapper.

Gemini / OpenAI / Anthropic 세 가지 provider 를 단일 함수
`call_llm()` 으로 호출할 수 있도록 추상화합니다.

LLM 호출은 반드시 이 모듈을 통해서만 이루어져야 합니다.
(provider 교체/모델 교체/재시도 로직 변경 시 단일 지점에서 처리)
"""

from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any

from backend.core.settings import get_settings, load_agents_config

logger = logging.getLogger(__name__)


# =====================================================================
# 응답 데이터 클래스
# =====================================================================
@dataclass
class LLMResponse:
    """LLM 호출 결과."""

    content: str                       # raw text 응답
    parsed: dict[str, Any] | None      # JSON 파싱 성공 시 dict, 실패 시 None
    model_id: str
    duration_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


# =====================================================================
# 모델 별칭 → 실제 모델 ID + provider 매핑
# =====================================================================
def _resolve_model(model_alias: str) -> tuple[str, str]:
    """model_alias 를 (provider, model_id) 로 변환.

    Returns:
        (provider, model_id) — provider 는 "gemini" | "openai" | "anthropic"
    """
    agents_config = load_agents_config()
    models: dict[str, str] = agents_config.get("models", {})

    if model_alias not in models:
        raise ValueError(
            f"알 수 없는 model_alias: '{model_alias}'.\n"
            f"config/agents.yaml 의 models 섹션에 정의된 키를 사용하세요. "
            f"현재 사용 가능한 별칭: {list(models.keys())}"
        )

    model_id = models[model_alias]
    if model_alias.startswith("gemini"):
        provider = "gemini"
    elif model_alias.startswith("openai"):
        provider = "openai"
    elif model_alias.startswith("anthropic"):
        provider = "anthropic"
    else:
        raise ValueError(
            f"model_alias '{model_alias}' 의 provider 를 추정할 수 없습니다. "
            "별칭은 gemini_/openai_/anthropic_ 로 시작해야 합니다."
        )
    return provider, model_id


# =====================================================================
# 비용 추정 (대략적인 단가, 추후 정확한 값으로 업데이트)
# 단위: USD per 1M tokens (input, output)
# =====================================================================
_PRICE_TABLE: dict[str, tuple[float, float]] = {
    "gemini-2.5-pro": (1.25, 5.00),
    "gemini-2.5-flash": (0.075, 0.30),
    "gpt-5": (5.00, 15.00),                 # placeholder
    "claude-opus-4-7": (15.00, 75.00),      # placeholder
}


def estimate_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """간단한 토큰 기반 비용 추정."""
    if model_id not in _PRICE_TABLE:
        return 0.0
    in_price, out_price = _PRICE_TABLE[model_id]
    return (prompt_tokens / 1_000_000) * in_price + (completion_tokens / 1_000_000) * out_price


# =====================================================================
# Provider별 호출 함수 (lazy import — SDK 미설치 환경에서도 모듈 로드 가능)
# =====================================================================
def _call_gemini(
    *,
    prompt: str,
    system_instruction: str,
    model_id: str,
    grounding: bool,
) -> tuple[str, int, int]:
    """Gemini 호출. (content, prompt_tokens, completion_tokens) 반환."""
    from google import genai
    from google.genai import types

    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    tools = []
    if grounding:
        tools.append(types.Tool(google_search=types.GoogleSearch()))

    config = types.GenerateContentConfig(
        system_instruction=system_instruction or None,
        response_mime_type="application/json",
        tools=tools or None,
    )

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=config,
    )

    content = response.text or ""
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = getattr(usage, "prompt_token_count", 0) or 0
    completion_tokens = getattr(usage, "candidates_token_count", 0) or 0
    return content, prompt_tokens, completion_tokens


def _call_openai(
    *,
    prompt: str,
    system_instruction: str,
    model_id: str,
) -> tuple[str, int, int]:
    """OpenAI 호출."""
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or ""
    usage = response.usage
    return (
        content,
        getattr(usage, "prompt_tokens", 0) or 0,
        getattr(usage, "completion_tokens", 0) or 0,
    )


def _call_anthropic(
    *,
    prompt: str,
    system_instruction: str,
    model_id: str,
) -> tuple[str, int, int]:
    """Anthropic 호출.

    Anthropic 은 native JSON mode 가 없어, system prompt 에 JSON 강제 지시를 덧붙입니다.
    """
    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    json_hint = "\n\n반드시 유효한 JSON 객체 하나만 출력하세요. 다른 설명 텍스트는 포함하지 마세요."
    system = (system_instruction or "") + json_hint

    response = client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    # content 는 블록 리스트
    content_parts = [b.text for b in response.content if hasattr(b, "text")]
    content = "".join(content_parts)
    usage = response.usage
    return (
        content,
        getattr(usage, "input_tokens", 0) or 0,
        getattr(usage, "output_tokens", 0) or 0,
    )


# =====================================================================
# 공개 API
# =====================================================================
def call_llm(
    prompt: str,
    *,
    model_alias: str,
    system_instruction: str = "",
    grounding: bool = False,
    max_retries: int = 3,
) -> LLMResponse:
    """LLM 호출 단일 진입점.

    Args:
        prompt: 사용자 메시지.
        model_alias: config/agents.yaml 의 models 섹션 키.
                     (예: "gemini_pro", "gemini_flash", "openai_judge", "anthropic_judge")
        system_instruction: 시스템 프롬프트 (markdown 파일 내용 등).
        grounding: True 면 web search/grounding 활성화 (Gemini 만 지원).
        max_retries: 재시도 횟수 (지수 백오프).

    Returns:
        LLMResponse — content / parsed(JSON) / 토큰 / 비용 / 응답시간.
    """
    provider, model_id = _resolve_model(model_alias)

    if grounding and provider != "gemini":
        logger.warning(
            "grounding=True 는 현재 Gemini 만 지원합니다. "
            "provider=%s 에서는 무시됩니다.",
            provider,
        )

    last_error: Exception | None = None
    for attempt in range(max_retries):
        start = time.monotonic()
        try:
            if provider == "gemini":
                content, p_tok, c_tok = _call_gemini(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    model_id=model_id,
                    grounding=grounding,
                )
            elif provider == "openai":
                content, p_tok, c_tok = _call_openai(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    model_id=model_id,
                )
            elif provider == "anthropic":
                content, p_tok, c_tok = _call_anthropic(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    model_id=model_id,
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")

            duration_ms = int((time.monotonic() - start) * 1000)

            parsed: dict[str, Any] | None
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                parsed = None

            cost = estimate_cost(model_id, p_tok, c_tok)
            logger.info(
                "LLM call: provider=%s model=%s duration=%dms tokens=%d/%d cost=$%.4f",
                provider, model_id, duration_ms, p_tok, c_tok, cost,
            )

            return LLMResponse(
                content=content,
                parsed=parsed,
                model_id=model_id,
                duration_ms=duration_ms,
                prompt_tokens=p_tok,
                completion_tokens=c_tok,
                estimated_cost_usd=cost,
            )

        except Exception as e:  # noqa: BLE001 — 재시도 목적
            last_error = e
            wait = (2**attempt) + random.uniform(0, 1)
            logger.warning(
                "LLM 호출 실패 (attempt %d/%d, provider=%s, model=%s): %s. %.1f초 후 재시도.",
                attempt + 1, max_retries, provider, model_id, e, wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)

    raise RuntimeError(
        f"LLM 호출이 {max_retries}회 모두 실패했습니다. "
        f"provider={provider} model={model_id} 마지막 에러: {last_error}"
    )

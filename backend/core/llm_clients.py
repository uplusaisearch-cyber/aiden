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

from backend.core.cost_tracker import LLMBudgetExceeded, get_cost_tracker
from backend.core.settings import get_settings, load_agents_config

logger = logging.getLogger(__name__)


# =====================================================================
# Dry-run: 실제 호출 없이 예상 비용만 산정
# =====================================================================
def _estimate_dry_run_tokens(prompt: str, system: str) -> tuple[int, int]:
    """매우 거친 토큰 추정 (한국어 ≈ 1 token / 2 chars 기준).

    정확도보다는 ‘대략적인 자릿수’ 가 중요합니다.
    """
    in_chars = len(prompt or "") + len(system or "")
    in_tokens = max(50, in_chars // 2)
    out_tokens = 500  # 에이전트 평균 JSON 응답 가정
    return in_tokens, out_tokens


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
    run_id: str | None = None,
) -> LLMResponse:
    """LLM 호출 단일 진입점.

    Args:
        prompt: 사용자 메시지.
        model_alias: config/agents.yaml 의 models 섹션 키.
                     (예: "gemini_pro", "gemini_flash", "openai_judge", "anthropic_judge")
        system_instruction: 시스템 프롬프트 (markdown 파일 내용 등).
        grounding: True 면 web search/grounding 활성화 (Gemini 만 지원).
        max_retries: 재시도 횟수 (지수 백오프).
        run_id: 단일 Topic Newsroom 실행을 식별하는 문자열. CostTracker 가 이
            값을 기준으로 run 단위 호출수/비용 한도를 검사합니다. None 이면
            run 단위 검사는 생략됩니다 (일일/월간 검사는 항상 적용).

    Returns:
        LLMResponse — content / parsed(JSON) / 토큰 / 비용 / 응답시간.

    Raises:
        LLMBudgetExceeded: 일일/월간/run 예산 초과.
        RuntimeError: 재시도 모두 실패 시.
    """
    settings = get_settings()
    safety_mode = (settings.safety_mode or "development").lower()
    provider, model_id = _resolve_model(model_alias)

    # ------------------------------------------------------------------
    # Dry-run: 실제 호출 X, 예상 비용만 출력
    # ------------------------------------------------------------------
    if safety_mode == "dry_run":
        in_tok, out_tok = _estimate_dry_run_tokens(prompt, system_instruction)
        cost = estimate_cost(model_id, in_tok, out_tok)
        payload: dict[str, Any] = {
            "_dry_run": True,
            "model_alias": model_alias,
            "model_id": model_id,
            "estimated_tokens_in": in_tok,
            "estimated_tokens_out": out_tok,
            "estimated_cost_usd": round(cost, 6),
        }
        content = json.dumps(payload, ensure_ascii=False)
        logger.info(
            "[dry_run] model=%s tokens≈%d/%d est_cost≈$%.5f (실제 호출 스킵)",
            model_id, in_tok, out_tok, cost,
        )
        return LLMResponse(
            content=content,
            parsed=payload,
            model_id=model_id,
            duration_ms=0,
            prompt_tokens=in_tok,
            completion_tokens=out_tok,
            estimated_cost_usd=cost,
        )

    if grounding and provider != "gemini":
        logger.warning(
            "grounding=True 는 현재 Gemini 만 지원합니다. "
            "provider=%s 에서는 무시됩니다.",
            provider,
        )

    # ------------------------------------------------------------------
    # 예산 사전 검사 (초과 시 LLMBudgetExceeded)
    # ------------------------------------------------------------------
    tracker = get_cost_tracker()
    tracker.precheck(run_id=run_id)

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

            # 성공한 호출만 누적
            tracker.record(cost, run_id=run_id)

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

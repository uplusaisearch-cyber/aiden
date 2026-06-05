"""Anthropic async 래퍼 (Judge Panel 전용).

Anthropic SDK 는 native JSON mode 가 없어 system prompt 에 JSON 강제 지시 부가.
JudgePanel 이 ``asyncio.gather`` 로 3 모델을 동시 호출하기 위해 비동기 인터페이스 제공.

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.runtime_keys import get_provider_key
from backend.core.settings import get_settings

logger = logging.getLogger(__name__)

_JSON_HINT = (
    "\n\n반드시 유효한 JSON 객체 하나만 출력하세요. "
    "코드펜스, 설명, 사족 없이 JSON 본문만 포함해야 합니다."
)


def _strip_code_fence(text: str) -> str:
    """Claude 가 가끔 ```json ... ``` 펜스를 붙이면 제거."""
    s = text.strip()
    if s.startswith("```"):
        # 첫 줄(``` 또는 ```json) 제거
        lines = s.split("\n", 1)
        s = lines[1] if len(lines) > 1 else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


async def call_anthropic_judge(
    *,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    timeout_sec: float = 60.0,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Anthropic 모델로 평가 호출 (JSON 강제).

    Args:
        model_id: 실제 모델 ID (예: "claude-opus-4-7"). resolver 가 결정.
        system_prompt: judge 프롬프트 .md 파일 내용.
        user_prompt: 평가 대상 HTML 등 사용자 입력.
        timeout_sec: 단일 호출 타임아웃 (초).
        max_tokens: 응답 최대 토큰.

    Returns:
        파싱된 평가 dict (공통 JSON 스키마).

    Raises:
        json.JSONDecodeError: 모델 응답이 JSON 이 아닌 경우.
        Exception: SDK 에러.
    """
    from anthropic import AsyncAnthropic

    # B3-S3-E A2: 런타임 override > env. JSON 강제 prompt 후처리는 변경 금지.
    api_key = get_provider_key("anthropic") or get_settings().anthropic_api_key
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 가 설정되지 않았습니다. .env 또는 어드민 키 페이지를 확인하세요."
        )

    client = AsyncAnthropic(api_key=api_key, timeout=timeout_sec)

    response = await client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        system=(system_prompt or "") + _JSON_HINT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    content_parts = [b.text for b in response.content if hasattr(b, "text")]
    raw = "".join(content_parts)
    cleaned = _strip_code_fence(raw)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Anthropic 응답이 JSON object 가 아닙니다: type={type(parsed).__name__}"
        )
    return parsed

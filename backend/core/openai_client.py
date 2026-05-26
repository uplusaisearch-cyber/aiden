"""OpenAI async 래퍼 (Judge Panel 전용).

JudgePanel 이 ``asyncio.gather`` 로 3 모델을 동시 호출하기 위해 비동기 인터페이스를
별도 모듈로 분리. 동기 호출은 ``backend/core/llm_clients.py`` 의 ``call_llm()`` 사용.

명세: docs/patches/2026-05-25_bundle3_step2_judge_panel_v2.md
"""
from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.settings import get_settings

logger = logging.getLogger(__name__)


async def call_openai_judge(
    *,
    model_id: str,
    system_prompt: str,
    user_prompt: str,
    timeout_sec: float = 60.0,
) -> dict[str, Any]:
    """OpenAI 모델로 평가 호출 (JSON mode).

    Args:
        model_id: 실제 모델 ID (예: "gpt-5"). resolver 가 결정.
        system_prompt: judge 프롬프트 .md 파일 내용.
        user_prompt: 평가 대상 HTML 등 사용자 입력.
        timeout_sec: 단일 호출 타임아웃 (초).

    Returns:
        파싱된 평가 dict (공통 JSON 스키마).

    Raises:
        json.JSONDecodeError: 모델 응답이 JSON 이 아닌 경우.
        Exception: SDK 에러 (rate limit / auth / network 등).
    """
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY 가 설정되지 않았습니다. .env 를 확인하세요."
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=timeout_sec)

    response = await client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or ""
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError(f"OpenAI 응답이 JSON object 가 아닙니다: type={type(parsed).__name__}")
    return parsed

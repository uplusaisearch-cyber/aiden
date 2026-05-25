"""Gemini API 클라이언트 (google-genai 신규 SDK).

목적: system_prompt + user_input(dict) → JSON dict 반환.
Grounding 옵션 지원 (Trend Scout / Fact-Checker 용).

⚠️ 제약: Gemini API 는 tools(Grounding) + ``response_mime_type='application/json'``
   동시 미지원. Grounding 사용 시 mime_type 안 쓰고 prompt 기반 JSON 강제 (옵션 B).

의존: ``google-genai`` (구 ``google-generativeai`` 와 다름)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    logger.warning("google-genai 미설치. pip install google-genai")


# 기본 모델 (2026-05 기준)
DEFAULT_MODEL = "gemini-2.5-flash"

# Grounding 사용 시 JSON 강제용 추가 지시 (response_mime_type 못 박을 때)
JSON_FORCE_SUFFIX = (
    "\n\n출력 형식: 반드시 단일 JSON 객체만 반환하세요. "
    "코드블록(```)이나 JSON 외 텍스트(설명·주석·요약 등)는 절대 포함하지 마세요. "
    "응답의 첫 글자는 `{`, 마지막 글자는 `}` 여야 합니다."
)


class GeminiClient:
    """google-genai 기반 Gemini API wrapper.

    Usage:
        client = GeminiClient(api_key="...", model="gemini-2.5-flash")
        result_dict = client.call(
            system_prompt="...",
            user_input={"category": "맛집"},
            use_grounding=True,
        )

    제약:
        - ``use_grounding=True`` 일 때 ``response_mime_type='application/json'`` 사용 불가
          → prompt 에 JSON_FORCE_SUFFIX 추가하여 텍스트 모드에서 JSON 강제
        - ``use_grounding=False`` 일 때 ``response_mime_type='application/json'`` 사용
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
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
            raise ValueError(
                "API 키 미설정. .env 에 GOOGLE_AI_STUDIO_API_KEY 또는 GEMINI_API_KEY 설정 필요."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = model

    def call(
        self,
        system_prompt: str,
        user_input: dict,
        use_grounding: bool = False,
        temperature: float = 0.7,
    ) -> dict:
        """Gemini 호출 후 JSON dict 반환.

        Args:
            system_prompt: 에이전트 system prompt (PromptLoader 로 로드된).
            user_input: 에이전트 입력 dict.
            use_grounding: Google Search Grounding 사용 여부.
            temperature: 생성 temperature.

        Returns:
            파싱된 JSON dict.

        Raises:
            ValueError: JSON 파싱 실패 시.
        """
        # user_input 을 JSON 문자열로 직렬화해 전달
        user_message = (
            "다음 JSON 입력을 받아 system prompt의 출력 형식에 정확히 맞는 JSON만 반환해주세요.\n\n"
            f"입력:\n```json\n{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```"
        )

        # 시스템 프롬프트 조립
        effective_system_prompt = system_prompt
        if use_grounding:
            # Grounding 사용 시 mime_type 못 박으므로 prompt 로 JSON 강제
            effective_system_prompt = system_prompt + JSON_FORCE_SUFFIX

        # config 조립
        config_kwargs: dict[str, Any] = {
            "system_instruction": effective_system_prompt,
            "temperature": temperature,
        }

        if use_grounding:
            # Grounding tool 추가, mime_type 미사용
            config_kwargs["tools"] = [
                types.Tool(google_search=types.GoogleSearch())
            ]
        else:
            # JSON 모드
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise

        raw_text = self._extract_text(response)
        return self._parse_json(raw_text)

    @staticmethod
    def _extract_text(response: Any) -> str:
        """response 객체에서 text 추출. Grounding 시 candidates 구조가 다를 수 있음."""
        # 1순위: response.text (대부분 케이스)
        text = getattr(response, "text", None)
        if text:
            return text

        # 2순위: candidates[0].content.parts[*].text 합치기
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                parts = candidates[0].content.parts
                texts = [getattr(p, "text", "") for p in parts]
                joined = "".join(t for t in texts if t)
                if joined:
                    return joined
        except Exception as e:
            logger.warning(f"Failed to extract text from candidates: {e}")

        return ""

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

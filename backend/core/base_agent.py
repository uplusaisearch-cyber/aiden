"""Agent 베이스 클래스.

각 에이전트는 다음 세 가지로 정의됩니다:
1. 이름 (name)
2. 사용 모델 (model_alias — config/agents.yaml 의 별칭)
3. system prompt 파일 경로 (backend/agents/prompts/*.md)

system prompt 를 markdown 파일에서 읽어오므로, 코드 수정 없이 텍스트
편집만으로 에이전트의 페르소나를 튜닝할 수 있습니다.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.llm_clients import LLMResponse, call_llm

logger = logging.getLogger(__name__)


@dataclass
class AgentRunLog:
    """Agent.run() 호출 1회분의 로그."""

    agent_name: str
    timestamp: str
    input_data: dict[str, Any]
    output: dict[str, Any]
    duration_ms: int
    model_id: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    raw_content: str = ""


class Agent:
    """모든 에이전트의 베이스.

    Args:
        name: 에이전트 이름 (예: "Trend Scout").
        model_alias: config/agents.yaml 의 models 섹션 키.
        prompt_file_path: system prompt 가 담긴 .md 파일 경로.
        grounding: True 면 web grounding 활성화 (Gemini 만 지원).
    """

    def __init__(
        self,
        name: str,
        model_alias: str,
        prompt_file_path: str | Path,
        grounding: bool = False,
    ):
        self.name = name
        self.model_alias = model_alias
        self.prompt_file_path = Path(prompt_file_path)
        self.grounding = grounding
        self.logs: list[AgentRunLog] = []

        # system prompt 는 인스턴스 생성 시 한 번만 로드
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # System prompt 로딩
    # ------------------------------------------------------------------
    def _load_system_prompt(self) -> str:
        if not self.prompt_file_path.exists():
            raise FileNotFoundError(
                f"[{self.name}] system prompt 파일을 찾을 수 없습니다: "
                f"{self.prompt_file_path}"
            )
        return self.prompt_file_path.read_text(encoding="utf-8")

    def reload_prompt(self) -> None:
        """system prompt 파일을 다시 읽어 갱신합니다 (런타임 튜닝용)."""
        self._system_prompt = self._load_system_prompt()

    # ------------------------------------------------------------------
    # 실행
    # ------------------------------------------------------------------
    def run(self, input_data: dict[str, Any], *, max_json_retries: int = 2) -> dict[str, Any]:
        """에이전트 실행.

        input_data 를 JSON 으로 직렬화해서 user prompt 로 전달합니다.
        응답이 JSON 파싱에 실패하면 max_json_retries 만큼 재시도합니다.

        Returns:
            파싱된 dict 응답.
        """
        user_prompt = self._build_user_prompt(input_data)
        start = time.monotonic()

        last_response: LLMResponse | None = None
        for attempt in range(max_json_retries + 1):
            response = call_llm(
                prompt=user_prompt,
                model_alias=self.model_alias,
                system_instruction=self._system_prompt,
                grounding=self.grounding,
            )
            last_response = response

            if response.parsed is not None:
                output = response.parsed
                break

            logger.warning(
                "[%s] JSON 파싱 실패 (attempt %d/%d). raw content head: %s",
                self.name, attempt + 1, max_json_retries + 1,
                response.content[:200],
            )
            # 다음 시도에선 좀 더 강한 지시를 덧붙임
            user_prompt = (
                self._build_user_prompt(input_data)
                + "\n\n[중요] 직전 응답이 유효한 JSON 이 아니었습니다. "
                "코드블록/설명/마크다운 없이 **순수 JSON 객체 하나만** 반환하세요."
            )
        else:
            raise RuntimeError(
                f"[{self.name}] 응답을 JSON 으로 파싱할 수 없습니다 "
                f"({max_json_retries + 1}회 시도). "
                f"raw content head: {(last_response.content if last_response else '')[:300]}"
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        assert last_response is not None
        log_entry = AgentRunLog(
            agent_name=self.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_data=input_data,
            output=output,
            duration_ms=duration_ms,
            model_id=last_response.model_id,
            tokens_in=last_response.prompt_tokens,
            tokens_out=last_response.completion_tokens,
            cost_usd=last_response.estimated_cost_usd,
            raw_content=last_response.content,
        )
        self.logs.append(log_entry)
        logger.info(
            "[%s] 실행 완료 — %dms, $%.4f",
            self.name, duration_ms, last_response.estimated_cost_usd,
        )
        return output

    def _build_user_prompt(self, input_data: dict[str, Any]) -> str:
        """input_data 를 보기 좋은 JSON 문자열로 직렬화."""
        return json.dumps(input_data, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # 디버그/관찰용
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"Agent(name={self.name!r}, model_alias={self.model_alias!r}, "
            f"grounding={self.grounding})"
        )

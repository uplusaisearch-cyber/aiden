"""AIDEN 오케스트레이터 베이스.

각 Newsroom(Stage 1/2/3)은 BaseNewsroom 상속.
미니 state-machine: 단계 정의 + 실행 + 트레이스 기록.
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable

from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """에이전트 실행 중 발생한 오류 (오케스트레이터는 raise 안 함, 내부에서 처리)."""

    pass


class BaseNewsroom(ABC):
    """Newsroom 베이스 클래스.

    하위 클래스는 다음을 구현:
      - run: 메인 실행 메서드
    """

    def __init__(self, tracer: TraceLogger):
        self.tracer = tracer

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> dict:
        """메인 실행 메서드. 하위 클래스에서 구현."""
        ...

    def _execute_agent(
        self,
        order: int,
        agent_name: str,
        agent_callable: Callable[[dict], dict],
        input_data: dict,
        iteration: int | None = None,
        max_retries: int = 1,
    ) -> tuple[dict, str | None]:
        """단일 에이전트 실행 + 트레이스 기록.

        Args:
            order: 실행 순서.
            agent_name: snake_case.
            agent_callable: ``callable(input_data: dict) -> dict``.
            input_data: 입력.
            iteration: Content Newsroom 의 iter (없으면 None).
            max_retries: JSON 파싱 실패 시 재시도 횟수 (default 1).

        Returns:
            ``(output_data, error_message or None)``
        """
        start = time.time()
        error: str | None = None
        output_data: dict = {}

        for attempt in range(max_retries + 1):
            try:
                output_data = agent_callable(input_data)
                if not isinstance(output_data, dict):
                    raise AgentExecutionError(
                        f"Agent {agent_name} did not return dict: "
                        f"got {type(output_data).__name__}"
                    )
                error = None
                break
            except Exception as e:
                error = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"Agent {agent_name} attempt {attempt + 1} failed: {error}"
                )
                if attempt < max_retries:
                    time.sleep(0.5)  # short backoff

        duration_ms = int((time.time() - start) * 1000)

        self.tracer.log_agent_step(
            order=order,
            agent_name=agent_name,
            iteration=iteration,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            error=error,
        )

        return output_data, error

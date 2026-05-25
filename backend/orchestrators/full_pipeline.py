"""AIDEN 전체 파이프라인 통합.

Topic Newsroom → Content Newsroom → Game-ifier
하나의 TraceLogger 를 공유하여 9개 에이전트 trace 가 동일 run_id 에 누적됨.
"""
from __future__ import annotations

import logging
from typing import Callable

from .content_newsroom import ContentNewsroom
from .gameifier import Gameifier
from .topic_newsroom import TopicNewsroom
from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class FullPipeline:
    """AIDEN 전체 파이프라인.

    Usage:
        pipeline = FullPipeline(
            tracer=tracer,
            agents=agent_dict,  # 9개 에이전트 callable
        )
        result = pipeline.run(category="맛집")
    """

    def __init__(
        self,
        tracer: TraceLogger,
        agents: dict[str, Callable[[dict], dict]],
    ):
        """Args:
            tracer: TraceLogger 인스턴스 (모든 에이전트 공유).
            agents: 키는 다음 9개 —
                ``scout``, ``analyst``, ``planner``,
                ``writer``, ``fact_checker``, ``devils_advocate``, ``editor``,
                ``format_architect``, ``html_builder``.
        """
        self.tracer = tracer
        self.agents = agents
        self._validate_agents()

    def _validate_agents(self) -> None:
        required = {
            "scout", "analyst", "planner",
            "writer", "fact_checker", "devils_advocate", "editor",
            "format_architect", "html_builder",
        }
        missing = required - set(self.agents.keys())
        if missing:
            raise ValueError(f"FullPipeline 누락 에이전트: {missing}")

    def run(self, category: str, target_date: str | None = None) -> dict:
        """전체 파이프라인 실행.

        Returns:
            dict with:
                - stage_1: Topic Newsroom 결과
                - stage_2: Content Newsroom 결과
                - stage_3: Game-ifier 결과
                - final_html: 최종 HTML 문자열
                - status: ``completed`` | ``partial`` | ``failed_stage_N``
        """
        result: dict = {
            "stage_1": None,
            "stage_2": None,
            "stage_3": None,
            "final_html": None,
            "status": "started",
        }

        # Stage 1: Topic Newsroom
        logger.info("Stage 1: Topic Newsroom")
        tn = TopicNewsroom(
            tracer=self.tracer,
            scout_fn=self.agents["scout"],
            analyst_fn=self.agents["analyst"],
            planner_fn=self.agents["planner"],
        )
        stage_1 = tn.run(category=category, target_date=target_date)
        result["stage_1"] = stage_1

        if "final_topic" not in stage_1:
            logger.error("Stage 1 실패: final_topic 없음")
            result["status"] = "failed_stage_1"
            return result

        # Stage 2: Content Newsroom
        logger.info("Stage 2: Content Newsroom")
        cn = ContentNewsroom(
            tracer=self.tracer,
            writer_fn=self.agents["writer"],
            fact_checker_fn=self.agents["fact_checker"],
            devils_advocate_fn=self.agents["devils_advocate"],
            editor_fn=self.agents["editor"],
            base_order=4,
        )
        stage_2 = cn.run(category=category, strategy=stage_1["final_topic"])
        result["stage_2"] = stage_2

        if "final_content" not in stage_2:
            logger.error("Stage 2 실패: final_content 없음")
            result["status"] = "failed_stage_2"
            return result

        # Stage 3: Game-ifier
        logger.info("Stage 3: Game-ifier")
        gi = Gameifier(
            tracer=self.tracer,
            format_architect_fn=self.agents["format_architect"],
            html_builder_fn=self.agents["html_builder"],
            base_order=8,
        )
        stage_3 = gi.run(final_content=stage_2["final_content"])
        result["stage_3"] = stage_3
        result["final_html"] = stage_3.get("html")

        if stage_3.get("error"):
            result["status"] = "partial"  # Stage 3 fallback 사용된 케이스
        else:
            result["status"] = "completed"

        return result

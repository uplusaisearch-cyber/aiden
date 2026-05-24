"""Topic Newsroom (Stage 1).

흐름: Trend Scout → Audience Analyst → Strategy Planner
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable

from .base_newsroom import BaseNewsroom
from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class TopicNewsroom(BaseNewsroom):
    """Stage 1: 사용자가 입력한 category 로부터 final_topic 도출.

    Usage:
        tn = TopicNewsroom(
            tracer=tracer,
            scout_fn=scout_callable,
            analyst_fn=analyst_callable,
            planner_fn=planner_callable,
        )
        result = tn.run(category="맛집")
    """

    def __init__(
        self,
        tracer: TraceLogger,
        scout_fn: Callable[[dict], dict],
        analyst_fn: Callable[[dict], dict],
        planner_fn: Callable[[dict], dict],
    ):
        super().__init__(tracer)
        self.scout_fn = scout_fn
        self.analyst_fn = analyst_fn
        self.planner_fn = planner_fn

    def run(self, category: str, target_date: str | None = None) -> dict:
        """Topic Newsroom 실행.

        Args:
            category: 사용자 입력 카테고리.
            target_date: 트렌드 검색 기준일 (ISO 형식). None 이면 오늘.

        Returns:
            Strategy Planner 출력 (``final_topic`` 포함). 실패 시 partial dict.
        """
        if target_date is None:
            target_date = date.today().isoformat()

        # Step 1: Trend Scout
        scout_input = {
            "category": category,
            "target_date": target_date,
        }
        scout_output, scout_err = self._execute_agent(
            order=1,
            agent_name="trend_scout",
            agent_callable=self.scout_fn,
            input_data=scout_input,
        )
        if scout_err or not scout_output.get("trending_topics"):
            logger.error(f"Trend Scout failed or returned empty: {scout_err}")
            return {"error": "trend_scout_failed", "partial": scout_output}

        # Step 2: Audience Analyst
        analyst_input = {
            "category": scout_output.get("category", category),
            "trending_topics": scout_output["trending_topics"],
            # summary, search_queries_used는 의도적으로 제외 (data_flow_spec §2-2)
        }
        analyst_output, analyst_err = self._execute_agent(
            order=2,
            agent_name="audience_analyst",
            agent_callable=self.analyst_fn,
            input_data=analyst_input,
        )
        if analyst_err or not analyst_output.get("audience_evaluation"):
            logger.error(f"Audience Analyst failed: {analyst_err}")
            return {"error": "audience_analyst_failed", "partial": analyst_output}

        # Step 3: Strategy Planner
        planner_input = {
            "category": scout_output.get("category", category),
            "trend_scout": scout_output,
            "audience_analyst": analyst_output,
        }
        planner_output, planner_err = self._execute_agent(
            order=3,
            agent_name="strategy_planner",
            agent_callable=self.planner_fn,
            input_data=planner_input,
        )
        if planner_err or not planner_output.get("final_topic"):
            logger.error(f"Strategy Planner failed: {planner_err}")
            return {"error": "strategy_planner_failed", "partial": planner_output}

        return planner_output

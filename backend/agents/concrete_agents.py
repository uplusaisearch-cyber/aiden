"""구체 에이전트 callable 모음.

각 에이전트는 ``base_newsroom._execute_agent`` 에 callable 로 전달됨.
``agent_callable(input_data: dict) -> dict`` 시그니처.
"""
from __future__ import annotations

import logging
from typing import Callable

from backend.core.base_agent import PromptLoader
from backend.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def make_agent_callable(
    prompt_filename: str,
    llm_client: GeminiClient,
    use_grounding: bool = False,
    prompt_loader: PromptLoader | None = None,
) -> Callable[[dict], dict]:
    """prompt 파일과 LLM 클라이언트로부터 에이전트 callable 생성.

    Args:
        prompt_filename: 예 "04_writer.md".
        llm_client: GeminiClient 인스턴스.
        use_grounding: Google Search Grounding 사용 여부.
        prompt_loader: 재사용 시 인스턴스 주입 (None 이면 새로 생성).

    Returns:
        ``agent_callable(input_data: dict) -> dict``.
    """
    loader = prompt_loader or PromptLoader()
    system_prompt = loader.load(prompt_filename)

    def _call(input_data: dict) -> dict:
        return llm_client.call(
            system_prompt=system_prompt,
            user_input=input_data,
            use_grounding=use_grounding,
        )

    _call.__name__ = f"agent_{prompt_filename.replace('.md', '')}"
    return _call


def build_topic_newsroom_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """Topic Newsroom 용 3개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "scout": make_agent_callable(
            "01_trend_scout.md", llm_client, use_grounding=True, prompt_loader=loader
        ),
        "analyst": make_agent_callable(
            "02_audience_analyst.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "planner": make_agent_callable(
            "03_strategy_planner.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }


def build_content_newsroom_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """Content Newsroom 용 4개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "writer": make_agent_callable(
            "04_writer.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "fact_checker": make_agent_callable(
            "05_fact_checker.md", llm_client, use_grounding=True, prompt_loader=loader
        ),
        "devils_advocate": make_agent_callable(
            "06_devils_advocate.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "editor": make_agent_callable(
            "07_editor_in_chief.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }


def build_gameifier_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """Game-ifier 용 2개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "format_architect": make_agent_callable(
            "08_format_architect.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "html_builder": make_agent_callable(
            "09_html_builder.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }


def build_all_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """9개 에이전트 전체 callable 생성. FullPipeline 입력용."""
    loader = PromptLoader()

    topic = {
        "scout": make_agent_callable(
            "01_trend_scout.md", llm_client, use_grounding=True, prompt_loader=loader
        ),
        "analyst": make_agent_callable(
            "02_audience_analyst.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "planner": make_agent_callable(
            "03_strategy_planner.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }
    content = {
        "writer": make_agent_callable(
            "04_writer.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "fact_checker": make_agent_callable(
            "05_fact_checker.md", llm_client, use_grounding=True, prompt_loader=loader
        ),
        "devils_advocate": make_agent_callable(
            "06_devils_advocate.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "editor": make_agent_callable(
            "07_editor_in_chief.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }
    game = {
        "format_architect": make_agent_callable(
            "08_format_architect.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "html_builder": make_agent_callable(
            "09_html_builder.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }
    return {**topic, **content, **game}

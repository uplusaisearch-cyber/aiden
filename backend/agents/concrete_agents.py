"""구체 에이전트 callable 모음.

각 에이전트는 ``base_newsroom._execute_agent`` 에 callable 로 전달됨.
``agent_callable(input_data: dict) -> dict`` 시그니처.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from backend.core.base_agent import PromptLoader
from backend.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)

# 모든 에이전트에 부착되는 안전 폴백. 503/429/빈 응답 시 강등.
_FALLBACK_MODEL = "gemini-2.5-flash-lite"


def _build_client_for_alias(
    alias: str,
    model_aliases: dict[str, str],
) -> GeminiClient:
    """yaml ``models.<alias>`` → ``GeminiClient`` 인스턴스.

    우선순위:
        1) env ``AIDEN_GEMINI_MODELS`` (콤마 구분) — 디버그 override. 설정되면 모든
           에이전트가 동일 chain 사용 (운영 일괄 강등용).
        2) yaml ``models.<alias>`` 의 model_id + ``_FALLBACK_MODEL`` 폴백.

    별칭 매핑이 없으면 ``gemini-2.5-flash`` 안전 폴백 + warning.
    """
    env_chain_raw = os.environ.get("AIDEN_GEMINI_MODELS", "").strip()
    if env_chain_raw:
        chain = [m.strip() for m in env_chain_raw.split(",") if m.strip()]
        if chain:
            return GeminiClient(models=chain)

    primary = model_aliases.get(alias)
    if not primary:
        logger.warning(
            "config/agents.yaml models.%s 매핑 없음 → gemini-2.5-flash 안전 폴백",
            alias,
        )
        primary = "gemini-2.5-flash"

    chain = [primary] if primary == _FALLBACK_MODEL else [primary, _FALLBACK_MODEL]
    return GeminiClient(models=chain)


def make_agent_callable(
    prompt_filename: str,
    llm_client: GeminiClient,
    use_grounding: bool = False,
    prompt_loader: PromptLoader | None = None,
    dynamic_vars_fn: Callable[[], dict[str, str]] | None = None,
) -> Callable[[dict], dict]:
    """prompt 파일과 LLM 클라이언트로부터 에이전트 callable 생성.

    Args:
        prompt_filename: 예 "04_writer.md".
        llm_client: GeminiClient 인스턴스.
        use_grounding: Google Search Grounding 사용 여부.
        prompt_loader: 재사용 시 인스턴스 주입 (None 이면 새로 생성).
        dynamic_vars_fn: 호출 시점마다 system prompt 의 ``{{KEY}}`` 를 동적으로
            치환할 변수를 반환하는 함수. B3-S3-E 의 ``PUBLISHED_TOPICS`` 주입용.
            None 이면 정적 치환 (기존 동작).

    Returns:
        ``agent_callable(input_data: dict) -> dict``.
    """
    loader = prompt_loader or PromptLoader()
    # 정적 모드: 파일을 한 번만 읽어 캐시.
    if dynamic_vars_fn is None:
        system_prompt = loader.load(prompt_filename)

        def _call(input_data: dict) -> dict:
            return llm_client.call(
                system_prompt=system_prompt,
                user_input=input_data,
                use_grounding=use_grounding,
            )

        _call.__name__ = f"agent_{prompt_filename.replace('.md', '')}"
        return _call

    # 동적 모드: 매 호출마다 파일을 다시 읽고 dynamic_vars 도 substitute.
    prompt_path: Path = loader.prompts_dir / prompt_filename

    def _call(input_data: dict) -> dict:
        raw = prompt_path.read_text(encoding="utf-8")
        try:
            extra = dynamic_vars_fn() or {}
        except Exception as exc:  # noqa: BLE001 — 주입 실패가 파이프라인을 깨면 안 됨
            logger.warning("dynamic_vars_fn 실패 — placeholder 보존: %s", exc)
            extra = {}
        system_prompt = loader.substitute(raw, extra_vars=extra)
        return llm_client.call(
            system_prompt=system_prompt,
            user_input=input_data,
            use_grounding=use_grounding,
        )

    _call.__name__ = f"agent_{prompt_filename.replace('.md', '')}"
    return _call


# ---------------------------------------------------------------------
# B3-S3-E: Topic Scout PUBLISHED_TOPICS 동적 주입 헬퍼
# ---------------------------------------------------------------------
def _scout_dynamic_vars() -> dict[str, str]:
    """Topic Scout 호출 시점에 발행 토픽 레지스트리에서 PUBLISHED_TOPICS 블록을 만든다."""
    # 늦은 import — 순환 의존 / 테스트에서 registry 미초기화 환경 회피.
    from backend.api.services.topic_registry import render_published_topics_block

    return {"PUBLISHED_TOPICS": render_published_topics_block()}


# ---------------------------------------------------------------------
# B4-S2 C3: Strategy Planner INJECTED_* 동적 주입 헬퍼
# ---------------------------------------------------------------------
def _planner_dynamic_vars_factory(
    selection: dict | None,
) -> Callable[[], dict[str, str]]:
    """Strategy Planner system prompt 의 4개 placeholder 치환값 제공 함수.

    selection None / 누락 키 → 빈 문자열. 프롬프트의 "폴백 조건" 분기를 발동시켜
    angle/SEG 자율 결정 흐름을 유지 (회귀 방어).
    """
    sel = selection or {}

    def _vars() -> dict[str, str]:
        return {
            "INJECTED_ANGLE": str(sel.get("angle_label") or ""),
            "INJECTED_ANGLE_DIRECTIVE": str(sel.get("angle_directive") or ""),
            "INJECTED_SEGMENT": str(sel.get("segment_label") or ""),
            "INJECTED_SEGMENT_PERSONA": str(sel.get("segment_persona") or ""),
        }

    return _vars


# ---------------------------------------------------------------------
# 9 에이전트 사양: short_key → (prompt_filename, yaml_agent_key, use_grounding, dynamic_vars_fn)
# yaml_agent_key 는 config/agents.yaml 의 ``agents.<key>`` 매핑.
# use_grounding 은 yaml 의 ``grounding`` 와 OR 결합 (yaml=true 면 무조건 ON).
# ---------------------------------------------------------------------
_AGENT_SPECS: dict[str, tuple[str, str, bool, Callable[[], dict[str, str]] | None]] = {
    "scout":            ("01_trend_scout.md",        "trend_scout",       True,  _scout_dynamic_vars),
    "analyst":          ("02_audience_analyst.md",   "audience_analyst",  False, None),
    "planner":          ("03_strategy_planner.md",   "strategy_planner",  False, None),
    "writer":           ("04_writer.md",             "writer",            False, None),
    "fact_checker":     ("05_fact_checker.md",       "fact_checker",      True,  None),
    "devils_advocate":  ("06_devils_advocate.md",    "devils_advocate",   False, None),
    "editor":           ("07_editor_in_chief.md",    "editor_in_chief",   False, None),
    "format_architect": ("08_format_architect.md",   "format_architect",  False, None),
    "html_builder":     ("09_html_builder.md",       "html_builder",      False, None),
}


def _load_model_routing() -> tuple[dict[str, str], dict[str, dict]]:
    """config/agents.yaml 의 ``models`` 별칭 + ``agents`` 매핑 로드."""
    # 늦은 import — 테스트에서 yaml 미초기화 환경 회피.
    from backend.core.settings import load_agents_config

    cfg = load_agents_config()
    return cfg.get("models", {}) or {}, cfg.get("agents", {}) or {}


def _build_agents(
    short_keys: tuple[str, ...],
    planning_selection: dict | None = None,
) -> dict[str, Callable[[dict], dict]]:
    """yaml 매핑으로 에이전트별 GeminiClient 인스턴스 + callable 을 만든다.

    9 에이전트가 더 이상 단일 client 를 공유하지 않는다 — 에이전트별로 별칭 ↔
    실모델 ID 가 다를 수 있으며, ``config/agents.yaml`` 이 단일 출처가 된다.

    B4-S2 C3: ``planner`` 가 short_keys 에 포함되면 INJECTED_* 4개 키를 동적 주입.
    selection None 도 명시적으로 빈 문자열을 주입하여 프롬프트의 폴백 분기를 발동.
    """
    model_aliases, agents_cfg = _load_model_routing()
    loader = PromptLoader()
    planner_dyn_fn = _planner_dynamic_vars_factory(planning_selection)
    result: dict[str, Callable[[dict], dict]] = {}
    for short_key in short_keys:
        prompt_filename, yaml_key, default_grounding, dyn_fn = _AGENT_SPECS[short_key]
        # B4-S2 C3: planner 의 정적 None dyn_fn 을 selection-bound factory 로 교체.
        if short_key == "planner":
            dyn_fn = planner_dyn_fn
        spec = agents_cfg.get(yaml_key, {})
        alias = spec.get("model", "gemini_flash")
        # use_grounding: yaml 명시 우선, 미명시면 spec default.
        if "grounding" in spec:
            use_grounding = bool(spec["grounding"])
        else:
            use_grounding = default_grounding
        client = _build_client_for_alias(alias, model_aliases)
        result[short_key] = make_agent_callable(
            prompt_filename,
            client,
            use_grounding=use_grounding,
            prompt_loader=loader,
            dynamic_vars_fn=dyn_fn,
        )
    return result


def build_topic_newsroom_agents(
    llm_client: GeminiClient | None = None,
    planning_selection: dict | None = None,
) -> dict[str, Callable[[dict], dict]]:
    """Topic Newsroom 용 3개 에이전트 callable 생성.

    ``llm_client`` 는 호환을 위한 옵션 — 무시되며 yaml 매핑 기반 client 가 사용된다.
    ``planning_selection`` (B4-S2 C3) 은 planner 의 INJECTED_* 주입용. None 이면
    빈 문자열 주입 → 프롬프트 폴백 분기 발동.
    """
    if llm_client is not None:
        logger.debug("build_topic_newsroom_agents: llm_client 인자는 무시됨 (yaml 매핑 사용)")
    return _build_agents(("scout", "analyst", "planner"), planning_selection=planning_selection)


def build_content_newsroom_agents(
    llm_client: GeminiClient | None = None,
) -> dict[str, Callable[[dict], dict]]:
    """Content Newsroom 용 4개 에이전트 callable 생성."""
    if llm_client is not None:
        logger.debug("build_content_newsroom_agents: llm_client 인자는 무시됨 (yaml 매핑 사용)")
    return _build_agents(("writer", "fact_checker", "devils_advocate", "editor"))


def build_gameifier_agents(
    llm_client: GeminiClient | None = None,
) -> dict[str, Callable[[dict], dict]]:
    """Game-ifier 용 2개 에이전트 callable 생성."""
    if llm_client is not None:
        logger.debug("build_gameifier_agents: llm_client 인자는 무시됨 (yaml 매핑 사용)")
    return _build_agents(("format_architect", "html_builder"))


def build_all_agents(
    llm_client: GeminiClient | None = None,
    planning_selection: dict | None = None,
) -> dict[str, Callable[[dict], dict]]:
    """9개 에이전트 전체 callable 생성. FullPipeline 입력용.

    ``llm_client`` 는 legacy 시그니처 호환을 위한 옵션 — 무시된다.
    각 에이전트는 ``config/agents.yaml`` 의 ``agents.<key>.model`` 별칭으로
    별도 ``GeminiClient`` 를 받는다.

    ``planning_selection`` (B4-S2 C3): Strategy Planner 에 INJECTED_* 동적 주입.
    None 이면 빈 문자열 주입 → 프롬프트 폴백 분기 발동 (자율 흐름 유지).
    """
    if llm_client is not None:
        logger.debug("build_all_agents: llm_client 인자는 무시됨 (yaml 매핑 사용)")
    return _build_agents(tuple(_AGENT_SPECS.keys()), planning_selection=planning_selection)

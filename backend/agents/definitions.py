"""9 에이전트 인스턴스 정의.

config/agents.yaml 의 설정을 읽어 자동으로 Agent 인스턴스를 생성합니다.
외부에서는 다음과 같이 사용하세요:

    from backend.agents.definitions import all_agents, get_agent

    scout = get_agent("trend_scout")
    result = scout.run({"topic": "5G 요금제 비교"})
"""

from __future__ import annotations

from pathlib import Path

from backend.core.base_agent import Agent
from backend.core.settings import PROJECT_ROOT, load_agents_config

PROMPTS_DIR: Path = PROJECT_ROOT / "backend" / "agents" / "prompts"

# config key → (사람이 읽는 이름, 프롬프트 파일명) 매핑.
# 파일명은 prompts/ 폴더의 순서(01_, 02_, ...)를 그대로 사용.
_AGENT_SPECS: dict[str, tuple[str, str]] = {
    "trend_scout":      ("Trend Scout",       "01_trend_scout.md"),
    "audience_analyst": ("Audience Analyst",  "02_audience_analyst.md"),
    "strategy_planner": ("Strategy Planner",  "03_strategy_planner.md"),
    "writer":           ("Writer",            "04_writer.md"),
    "fact_checker":     ("Fact-Checker",      "05_fact_checker.md"),
    "devils_advocate":  ("Devil's Advocate",  "06_devils_advocate.md"),
    "editor_in_chief":  ("Editor-in-Chief",   "07_editor_in_chief.md"),
    "format_architect": ("Format Architect",  "08_format_architect.md"),
    "html_builder":     ("HTML Builder",      "09_html_builder.md"),
}


def _build_all_agents() -> dict[str, Agent]:
    """config/agents.yaml 을 기반으로 9개 Agent 를 생성합니다."""
    cfg = load_agents_config()
    agents_cfg: dict[str, dict] = cfg.get("agents", {})

    agents: dict[str, Agent] = {}
    for key, (display_name, prompt_filename) in _AGENT_SPECS.items():
        if key not in agents_cfg:
            raise KeyError(
                f"config/agents.yaml 의 agents 섹션에 '{key}' 가 정의되어 있지 않습니다."
            )
        spec = agents_cfg[key]
        agents[key] = Agent(
            name=display_name,
            model_alias=spec["model"],
            prompt_file_path=PROMPTS_DIR / prompt_filename,
            grounding=bool(spec.get("grounding", False)),
        )
    return agents


# 모듈 import 시점에 lazy 하게 생성되도록 함수로 노출.
# (테스트/CI 환경에서 prompt 파일이 비어 있어도 import 자체는 가능)
_cache: dict[str, Agent] | None = None


def all_agents() -> dict[str, Agent]:
    """9개 에이전트 dict 반환 (싱글톤)."""
    global _cache
    if _cache is None:
        _cache = _build_all_agents()
    return _cache


def get_agent(key: str) -> Agent:
    """key 로 단일 에이전트를 반환합니다.

    Args:
        key: _AGENT_SPECS 의 키 (예: "trend_scout").
    """
    agents = all_agents()
    if key not in agents:
        raise KeyError(
            f"알 수 없는 에이전트 키: '{key}'. "
            f"사용 가능한 키: {list(agents.keys())}"
        )
    return agents[key]

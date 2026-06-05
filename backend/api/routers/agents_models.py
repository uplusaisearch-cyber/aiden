"""GET /api/agents/models — 9 에이전트 + Judge 3종의 모델 매핑 노출.

config/agents.yaml 의 ``agents.<key>.model`` 별칭 → 실제 model_id 매핑을 프론트에
그대로 노출. UI 는 ChatMessage.agent_id (short key) 로 lookup 하여 채팅 버블 옆에
"3.1-pro-preview" 같은 짧은 라벨을 표시한다.

config 단일 출처 원칙: 별칭/매핑 변경은 yaml 한 곳에서만. UI 는 fetch 후 캐시.
"""
from __future__ import annotations

from fastapi import APIRouter

from backend.core.settings import load_agents_config, load_judge_panel_config

router = APIRouter(prefix="/api/agents", tags=["agents"])


# yaml agent_key → ChatMessage.agent_id 의 short key (frontend lookup key)
_SHORT_KEY: dict[str, str] = {
    "trend_scout":      "scout",
    "audience_analyst": "analyst",
    "strategy_planner": "planner",
    "writer":           "writer",
    "fact_checker":     "factchecker",
    "devils_advocate":  "devils",
    "editor_in_chief":  "editor",
    "format_architect": "architect",
    "html_builder":     "builder",
}


@router.get("/models")
def list_agent_models() -> dict:
    """9 newsroom 에이전트 + Judge 3종의 모델 매핑 반환."""
    cfg = load_agents_config()
    model_aliases: dict[str, str] = cfg.get("models", {}) or {}
    agents_cfg: dict[str, dict] = cfg.get("agents", {}) or {}

    newsroom: dict[str, dict] = {}
    for yaml_key, short_key in _SHORT_KEY.items():
        spec = agents_cfg.get(yaml_key, {})
        alias = spec.get("model", "gemini_flash")
        model_id = model_aliases.get(alias) or alias
        newsroom[short_key] = {
            "alias": alias,
            "model_id": model_id,
            "grounding": bool(spec.get("grounding", False)),
        }

    judges: dict[str, str] = {}
    try:
        judge_cfg = load_judge_panel_config()
        judges = dict(judge_cfg.get("models") or {})
    except Exception:  # noqa: BLE001 — judge 미설정도 newsroom 정보는 노출
        judges = {}

    return {"newsroom": newsroom, "judges": judges}

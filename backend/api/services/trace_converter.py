"""Raw trace JSON → ChatMessage 변환.

명세: docs/patches/2026-05-25_bundle3_step3_B_fastapi_sse_backend.md

12 에이전트별 1:1 변환 함수 + dispatch.
- 9 newsroom 에이전트 (scout/analyst/planner/writer/factchecker/devils/editor/architect/builder)
- judge_panel (1 input → 3 messages: gemini/gpt/claude)

ChatMessage 스키마 = backend/api/schemas/trace.py 의 ChatMessage 와 동일.
"""
from __future__ import annotations

import logging
from typing import Any, Callable
from uuid import uuid4

from backend.api.services.humanizer import humanize

logger = logging.getLogger(__name__)


# trace_logger 의 agent_name → frontend 의 AgentId 매핑
AGENT_NAME_TO_ID: dict[str, str] = {
    "trend_scout": "scout",
    "audience_analyst": "analyst",
    "strategy_planner": "planner",
    "writer": "writer",
    "fact_checker": "factchecker",
    "devils_advocate": "devils",
    "editor": "editor",
    "format_architect": "architect",
    "html_builder": "builder",
}


def _msg_id() -> str:
    return f"msg-{uuid4().hex[:10]}"


def _base(agent_id: str, raw: dict, stage: int) -> dict[str, Any]:
    """공통 필드. humanized 는 후처리(_apply_humanized) 에서 채움."""
    return {
        "id": _msg_id(),
        "agent_id": agent_id,
        "stage": stage,
        "iteration": raw.get("iteration"),
        "timestamp": raw.get("timestamp"),
        "duration_ms": raw.get("duration_ms", 0),
        "headline": "",
        "body_text": "",
        "humanized": "",
        "raw_json": raw.get("output") or {},
        "highlights": [],
        "badges": [],
    }


def _apply_humanized(msg: dict[str, Any], raw: dict[str, Any]) -> None:
    """ChatMessage 에 humanized 필드 채우기.

    humanizer 는 personas.yaml 의 키(짧은 id) 로 조회.
    judge-* 는 personas.yaml 에 없으므로 prefix/suffix 없는 summary 만 적용 (안전 폴백).
    실패 시 headline 만 그대로 사용 → 메인 흐름 차단 금지.
    """
    try:
        source_text = (msg.get("headline") or "").strip()
        body = (msg.get("body_text") or "").strip()
        if body:
            source_text = f"{source_text} {body}".strip()
        if not source_text:
            return
        msg["humanized"] = humanize(
            msg.get("agent_id", ""),
            source_text,
            raw.get("iteration"),
        )
    except Exception as e:  # noqa: BLE001 — humanizer 실패가 SSE 흐름을 막지 않게
        logger.warning("humanize 실패 (agent=%s): %s", msg.get("agent_id"), e)
        msg.setdefault("humanized", msg.get("headline") or "")


# =====================================================================
# 9 newsroom 에이전트 변환
# =====================================================================
def _convert_scout(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    topics = out.get("trending_topics") or []
    queries = out.get("search_queries_used") or []
    top = topics[0] if topics else {}
    msg = _base("scout", raw, stage=1)
    msg["headline"] = f"트렌드 {len(topics)}개 확보. 1위: '{top.get('topic') or top.get('title', '')}'"
    msg["body_text"] = f"검색 호출 {len(queries)}회, 후보 {len(topics)}개."
    msg["highlights"] = [
        {"label": "검색 호출", "value": f"{len(queries)}회"},
        {"label": "후보", "value": f"{len(topics)}개"},
    ]
    conf = top.get("confidence")
    if isinstance(conf, (int, float)):
        msg["highlights"].append({"label": "1위 신뢰도", "value": f"{conf:.2f}"})
        msg["badges"].append(
            {"label": "confidence", "value": "high" if conf > 0.8 else "medium",
             "color": "success" if conf > 0.8 else "warning"},
        )
    return [msg]


def _convert_analyst(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    verdict = out.get("verdict") or {}
    msg = _base("analyst", raw, stage=1)
    top_choice = verdict.get("top_choice_topic", "")
    msg["headline"] = f"1순위 추천: '{top_choice}'"
    msg["body_text"] = verdict.get("reasoning", "")[:200]
    persona_fit = verdict.get("persona_fit_score")
    if isinstance(persona_fit, (int, float)):
        msg["highlights"].append({"label": "페르소나 적합도", "value": f"{persona_fit:.2f}"})
    return [msg]


def _convert_planner(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    final = out.get("final_topic") or {}
    msg = _base("planner", raw, stage=1)
    title = final.get("title", "")
    msg["headline"] = f"앵글 확정: '{title[:50]}'"
    msg["body_text"] = final.get("angle", "")[:200]
    msg["highlights"] = [
        {"label": "타이틀", "value": title[:30]},
        {"label": "타겟", "value": final.get("target_persona", "")[:20]},
    ]
    return [msg]


def _convert_writer(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    title = out.get("title", "")
    sections = out.get("sections") or []
    draft_v = out.get("draft_version", raw.get("iteration"))
    msg = _base("writer", raw, stage=2)
    msg["headline"] = f"초안 v{draft_v} 완성. '{title[:40]}'"
    msg["body_text"] = f"섹션 {len(sections)}개, 글자수 약 {sum(len(s.get('body', '')) for s in sections)}자."
    msg["highlights"] = [
        {"label": "섹션", "value": f"{len(sections)}개"},
        {"label": "draft_v", "value": str(draft_v)},
    ]
    return [msg]


def _convert_factchecker(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    confidence = out.get("confidence_score", 0)
    log = out.get("verification_log") or []
    verified = sum(1 for v in log if v.get("status") == "verified")
    total = len(log)
    msg = _base("factchecker", raw, stage=2)
    msg["headline"] = f"{verified}/{total} 검증 완료. 신뢰도 {confidence}/10"
    msg["body_text"] = (out.get("summary") or "")[:200]
    msg["highlights"] = [
        {"label": "검증 완료", "value": f"{verified}/{total}"},
        {"label": "confidence", "value": f"{confidence}/10"},
    ]
    color = "success" if confidence >= 7 else ("warning" if confidence >= 4 else "danger")
    msg["badges"] = [{"label": "score", "value": f"{confidence}/10", "color": color}]
    return [msg]


def _convert_devils(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    issues = out.get("critical_issues") or []
    scores = out.get("scores") or {}
    avg = sum(scores.values()) / len(scores) if scores else 0.0
    passed = bool(out.get("pass_threshold"))
    # 실제 스키마 키는 `problem` (06_devils_advocate.md). 구버전·테스트 호환 위해 `issue` fallback.
    first = issues[0] if issues else {}
    top_critique = first.get("problem") or first.get("issue") or ""
    msg = _base("devils", raw, stage=2)
    # 비판 톤은 personas.yaml 의 prefix/suffix_options 가 담당. 여기는 중립 통계만.
    msg["headline"] = f"{len(issues)}건 비판. 평균 {avg:.1f}"
    msg["body_text"] = f"1번: {top_critique[:80]}" if top_critique else ""
    msg["highlights"] = [
        {"label": "비판", "value": f"{len(issues)}건"},
        {"label": "평균", "value": f"{avg:.1f}"},
    ]
    msg["badges"] = [
        {"label": "pass", "value": "통과" if passed else "재작성",
         "color": "success" if passed else "danger"},
    ]
    return [msg]


def _convert_editor(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    decision = out.get("decision", "?")
    accepted = out.get("accepted_critiques") or []
    rejected = out.get("rejected_critiques") or []
    decision_label = {"approved": "승인", "needs_revision": "재작성"}.get(decision, decision)
    msg = _base("editor", raw, stage=2)
    msg["headline"] = f"iter {raw.get('iteration')} 결정: {decision_label}"
    msg["body_text"] = f"비판 {len(accepted)}건 수용, {len(rejected)}건 기각."
    msg["highlights"] = [
        {"label": "accepted", "value": f"{len(accepted)}건"},
        {"label": "rejected", "value": f"{len(rejected)}건"},
    ]
    msg["badges"] = [
        {"label": "decision", "value": decision_label,
         "color": "success" if decision == "approved" else "warning"},
    ]
    return [msg]


def _convert_architect(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    selected_type = out.get("selected_type", "?")
    interactive = (out.get("interactive") or {}).get("template", "none")
    msg = _base("architect", raw, stage=3)
    msg["headline"] = f"타입 {selected_type} + 인터랙티브 '{interactive}'"
    # 실제 스키마 키 (08_format_architect.md): format_analysis 우선, type_reasoning fallback.
    # 구버전 `rationale` 도 최종 fallback 으로 받아 하위호환.
    body_source = (
        out.get("format_analysis")
        or out.get("type_reasoning")
        or out.get("rationale")
        or ""
    )
    msg["body_text"] = body_source[:200]
    msg["highlights"] = [
        {"label": "type", "value": selected_type},
        {"label": "interactive", "value": interactive},
    ]
    return [msg]


def _convert_builder(raw: dict) -> list[dict]:
    out = raw.get("output") or {}
    selected = out.get("selected_type_applied", "?")
    subs = out.get("placeholder_substitutions") or []
    preserved = out.get("preserved_placeholders") or []
    warns = out.get("warnings") or []
    msg = _base("builder", raw, stage=3)
    msg["headline"] = f"HTML 생성. 치환 {len(subs)}개"
    msg["body_text"] = f"보존 {len(preserved)}개, 경고 {len(warns)}건."
    msg["highlights"] = [
        {"label": "치환", "value": f"{len(subs)}개"},
        {"label": "보존", "value": f"{len(preserved)}개"},
        {"label": "warnings", "value": f"{len(warns)}건"},
    ]
    if warns:
        msg["badges"].append({"label": "warnings", "value": str(len(warns)), "color": "warning"})
    return [msg]


# =====================================================================
# Judge Panel: 1 input → 3 messages (per model)
# =====================================================================
def _convert_judge_panel(raw: dict) -> list[dict]:
    """judge_panel agent_step → 3개 message (gemini/gpt/claude)."""
    out = raw.get("output") or {}
    evals = out.get("evaluations") or {}
    msgs: list[dict] = []
    for model_key in ("gemini", "gpt", "claude"):
        ev = evals.get(model_key)
        agent_id = f"judge-{model_key}"
        if ev is None:
            msg = _base(agent_id, raw, stage=4)
            msg["headline"] = "평가 실패"
            msg["body_text"] = "(이 모델은 응답하지 않았습니다.)"
            msg["badges"] = [{"label": "status", "value": "failed", "color": "danger"}]
            msgs.append(msg)
            continue
        scores = ev.get("scores") or {}
        overall = ev.get("overall_score", 0)
        verdict = ev.get("one_line_verdict", "")
        strengths = ev.get("strengths") or []
        weaknesses = ev.get("weaknesses") or []
        msg = _base(agent_id, raw, stage=4)
        msg["headline"] = f"⭐ {overall} / 10 · {verdict}"
        msg["body_text"] = f"강점 {len(strengths)}건 / 약점 {len(weaknesses)}건"
        msg["highlights"] = [
            {"label": k, "value": v} for k, v in scores.items()
        ]
        color = "success" if overall >= 7 else ("warning" if overall >= 4 else "danger")
        msg["badges"] = [{"label": "overall", "value": f"{overall}/10", "color": color}]
        # raw_json 은 해당 모델 평가만 (전체 panel 결과 아님)
        msg["raw_json"] = ev
        msgs.append(msg)
    return msgs


# =====================================================================
# Dispatch
# =====================================================================
_DISPATCH: dict[str, Callable[[dict], list[dict]]] = {
    "trend_scout": _convert_scout,
    "audience_analyst": _convert_analyst,
    "strategy_planner": _convert_planner,
    "writer": _convert_writer,
    "fact_checker": _convert_factchecker,
    "devils_advocate": _convert_devils,
    "editor": _convert_editor,
    "format_architect": _convert_architect,
    "html_builder": _convert_builder,
    "judge_panel": _convert_judge_panel,
}


def convert(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """raw agent_step payload 를 ChatMessage 리스트로 변환.

    Args:
        raw: TraceLogger 가 publish 한 payload. 키:
            ``order``, ``agent_name``, ``iteration``, ``timestamp``,
            ``duration_ms``, ``input``, ``output``, ``error``, ``highlight``.

    Returns:
        ChatMessage dict 리스트. 보통 1개, judge_panel 만 3개.
    """
    agent_name = raw.get("agent_name", "")
    fn = _DISPATCH.get(agent_name)
    if fn is None:
        # 미정의 에이전트는 generic message 1개
        msg = _base(agent_name or "unknown", raw, stage=0)
        msg["headline"] = raw.get("highlight") or f"{agent_name} 완료"
        _apply_humanized(msg, raw)
        return [msg]
    try:
        messages = fn(raw)
    except Exception as e:  # noqa: BLE001 — 변환 실패가 SSE 흐름 막지 않게
        logger.warning("trace_converter %s 실패: %s", agent_name, e)
        msg = _base(agent_name, raw, stage=0)
        msg["headline"] = "(변환 실패) " + (raw.get("highlight") or agent_name)
        msg["body_text"] = str(e)
        _apply_humanized(msg, raw)
        return [msg]

    for m in messages:
        _apply_humanized(m, raw)
    return messages

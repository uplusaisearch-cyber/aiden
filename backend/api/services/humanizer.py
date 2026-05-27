"""룰베이스 사람말투 변환기.

명세: docs/patches/2026-05-28_b3-s3-c_trace_viewer.md (§3)

- personas.yaml 로드 후 lru_cache
- humanize(agent_id, raw_text, iter_no=None) -> str
- 결정론적: 같은 입력 -> 같은 출력 (md5 해시 기반 seed)
- agent_id 는 ChatMessage.agent_id (짧은 형태). aliases (full name) 로도 조회 가능.
"""
from __future__ import annotations

import hashlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# backend/api/services/humanizer.py -> backend/config/personas.yaml
_PERSONAS_PATH = Path(__file__).resolve().parents[2] / "config" / "personas.yaml"
_MAX_LEN = 280   # 채팅 버블 한 줄 안전 길이


@lru_cache(maxsize=1)
def load_personas() -> dict[str, Any]:
    """personas.yaml 로드. 파일 없으면 빈 dict 반환 (API 500 차단)."""
    if not _PERSONAS_PATH.exists():
        logger.warning("personas.yaml not found: %s", _PERSONAS_PATH)
        return {"version": 0, "personas": {}, "stages": {}}
    with _PERSONAS_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data.setdefault("personas", {})
    data.setdefault("stages", {})
    return data


@lru_cache(maxsize=1)
def _alias_map() -> dict[str, str]:
    """alias (full name) -> canonical short id 매핑."""
    out: dict[str, str] = {}
    for key, p in load_personas().get("personas", {}).items():
        for a in (p.get("aliases") or []):
            out[a] = key
    return out


def _resolve_agent_id(agent_id: str) -> str:
    """짧은 형태 또는 full name 어느 쪽이든 canonical key 로 정규화."""
    personas = load_personas().get("personas", {})
    if agent_id in personas:
        return agent_id
    return _alias_map().get(agent_id, agent_id)


def _seed_pick(options: list[str], seed_text: str) -> str:
    """raw_text 해시 기반 결정론적 선택."""
    if not options:
        return ""
    h = int(hashlib.md5(seed_text.encode("utf-8")).hexdigest(), 16)
    return options[h % len(options)]


def _summarize(raw_text: str, max_chars: int = 200) -> str:
    """원본 텍스트에서 첫 1~2 문장 추출. JSON / 코드 펜스 제거."""
    if not raw_text:
        return ""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(line for line in lines if not line.startswith("```"))
    cleaned = cleaned.strip()
    if not cleaned:
        return ""
    sentences: list[str] = []
    buf = ""
    for ch in cleaned:
        buf += ch
        if ch in "다.!?\n" and len(buf.strip()) > 5:
            sentences.append(buf.strip())
            buf = ""
            if len(sentences) >= 2:
                break
    if buf.strip():
        sentences.append(buf.strip())
    summary = " ".join(sentences)[:max_chars]
    return summary.rstrip()


def humanize(agent_id: str, raw_text: str, iter_no: int | None = None) -> str:
    """페르소나 prefix + 본문 요약 + suffix 를 합쳐 1~3 문장 반환.

    Args:
        agent_id: personas.yaml 키 또는 alias (예: "scout" 또는 "trend_scout")
        raw_text: LLM 원본 출력 또는 trace 요약
        iter_no: Content Newsroom iter 번호 (메타용, 변환 자체에는 미사용)

    Returns:
        "{prefix} {summary} {suffix}" 형태 문자열. 최대 _MAX_LEN.
    """
    key = _resolve_agent_id(agent_id)
    personas = load_personas().get("personas", {})
    p = personas.get(key)
    if not p:
        # 알 수 없는 에이전트: prefix/suffix 없이 summary 만
        return _summarize(raw_text)

    speech = p.get("speech") or {}
    seed = f"{key}::{(raw_text or '')[:50]}"
    prefix = _seed_pick(speech.get("prefix_options") or [], seed)
    suffix = _seed_pick(speech.get("suffix_options") or [], seed + "::suf")

    body_budget = _MAX_LEN - len(prefix) - len(suffix) - 4
    body_budget = max(0, body_budget)
    body = _summarize(raw_text, max_chars=body_budget)

    parts = [s for s in (prefix, body, suffix) if s]
    result = " ".join(parts).strip()
    return result[:_MAX_LEN]


def get_persona(agent_id: str) -> dict[str, Any] | None:
    """페르소나 메타 조회 (API 응답용)."""
    key = _resolve_agent_id(agent_id)
    return load_personas().get("personas", {}).get(key)


def get_all_personas() -> dict[str, Any]:
    """전체 personas + stages 반환."""
    return load_personas()

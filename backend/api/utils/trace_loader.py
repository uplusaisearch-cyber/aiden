"""runs/<session>/ 파일 시스템 로더.

API 가 GET /api/runs, /api/runs/{id} 호출 시 디스크의 trace 파일을 읽어 메타 추출.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

RUNS_DIR = PROJECT_ROOT / "runs"


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("JSON load 실패 %s: %s", path, e)
        return None


def _safe_read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return out


def list_run_sessions(runs_dir: Path | None = None) -> list[str]:
    """runs/ 폴더 안의 session id 목록 (최신순)."""
    base = runs_dir or RUNS_DIR
    if not base.exists():
        return []
    sessions = [p.name for p in base.iterdir() if p.is_dir()]
    # 이름이 ISO timestamp 로 시작하므로 사전 정렬 = 시간 정렬
    sessions.sort(reverse=True)
    return sessions


def load_run_summary(session_id: str, runs_dir: Path | None = None) -> dict[str, Any] | None:
    """단일 session 의 metadata.json + judge_panel.json 요약 dict 반환.

    None 이면 해당 session 폴더가 없거나 metadata.json 누락.
    """
    base = runs_dir or RUNS_DIR
    run_dir = base / session_id
    if not run_dir.exists() or not run_dir.is_dir():
        return None
    md = _safe_read_json(run_dir / "metadata.json")
    if md is None:
        # metadata 없으면 최소 정보만
        return {
            "session_id": session_id,
            "category": None,
            "title": None,
            "status": "unknown",
            "started_at": None,
            "duration_ms": None,
            "judge_weighted_total": None,
            "judge_status": None,
            "thumbnail_url": None,
        }
    jp = md.get("judge_panel") or {}
    user_input = md.get("user_input") or {}
    return {
        "session_id": session_id,
        "category": user_input.get("category"),
        "title": _extract_title(run_dir),
        "status": md.get("status", "unknown"),
        "started_at": md.get("started_at"),
        "duration_ms": (md.get("duration_sec") or 0) * 1000,
        "judge_weighted_total": jp.get("weighted_total"),
        "judge_status": jp.get("status"),
        "thumbnail_url": None,
    }


def _extract_title(run_dir: Path) -> str | None:
    """Stage 1 의 final_topic.title 또는 strategy_planner 결과에서 추출."""
    planner = _safe_read_json(run_dir / "agents" / "03_strategy_planner.json")
    if planner:
        ft = (planner.get("output") or {}).get("final_topic") or {}
        title = ft.get("title")
        if title:
            return title
    # fallback: summary.jsonl 에서 planner highlight 파싱
    return None


def load_run_detail(session_id: str, runs_dir: Path | None = None) -> dict[str, Any] | None:
    """전체 trace + judge_panel + metadata 통합."""
    base = runs_dir or RUNS_DIR
    run_dir = base / session_id
    if not run_dir.exists():
        return None

    metadata = _safe_read_json(run_dir / "metadata.json") or {}
    judge = _safe_read_json(run_dir / "judge_panel.json")
    summary_lines = _safe_read_jsonl(run_dir / "summary.jsonl")

    # 전체 agent step JSON 로드 → 변환은 호출자가 trace_converter 적용
    raw_steps: list[dict] = []
    agents_dir = run_dir / "agents"
    if agents_dir.exists():
        for p in sorted(agents_dir.glob("*.json")):
            d = _safe_read_json(p)
            if d:
                raw_steps.append(d)

    final_html_path = run_dir / "final_output.html"
    return {
        "session_id": session_id,
        "category": (metadata.get("user_input") or {}).get("category"),
        "status": metadata.get("status", "unknown"),
        "started_at": metadata.get("started_at"),
        "ended_at": metadata.get("ended_at"),
        "duration_sec": metadata.get("duration_sec"),
        "raw_steps": raw_steps,
        "summary_lines": summary_lines,
        "judge_panel": judge,
        "final_html_exists": final_html_path.exists(),
        "metadata": metadata,
    }


def load_final_html(session_id: str, runs_dir: Path | None = None) -> str | None:
    base = runs_dir or RUNS_DIR
    path = base / session_id / "final_output.html"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def session_exists(session_id: str, runs_dir: Path | None = None) -> bool:
    base = runs_dir or RUNS_DIR
    return (base / session_id).is_dir()


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

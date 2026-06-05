"""GET/PUT /api/prompts — 12 에이전트 system prompt CRUD + restore/history/rollback.

B3-S3-A 의 GET/PUT 위에 B3-S3-E (Persona Lab) 의 복원·롤백을 보강한 라우터.
새 admin 라우터를 따로 만들지 않고 이 파일을 단일 진입점으로 사용한다.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.schemas.prompt import (
    PromptDetail,
    PromptHistoryEntry,
    PromptHistoryResponse,
    PromptListResponse,
    PromptRestoreResponse,
    PromptRollbackRequest,
    PromptSummary,
    PromptUpdate,
    PromptUpdateResponse,
)
from backend.core.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["prompts"])

PROMPTS_DIR = PROJECT_ROOT / "backend" / "agents" / "prompts"
# B3-S3-A 의 기존 백업 폴더. B3-S3-E history 도 이 폴더를 재사용 (이름 통일).
VERSIONS_DIR = PROMPTS_DIR / ".versions"
# B3-S3-E restore 원본 스냅샷. 최초 부팅 시 1회 생성, 이후 불변.
DEFAULTS_DIR = PROMPTS_DIR / "_defaults"

# agent_id ↔ 파일명. 기존 B3-S3-A 매핑을 유지. (frontend 의 agent id 와 동일)
AGENT_PROMPT_FILES: dict[str, str] = {
    "scout": "01_trend_scout.md",
    "analyst": "02_audience_analyst.md",
    "planner": "03_strategy_planner.md",
    "writer": "04_writer.md",
    "factchecker": "05_fact_checker.md",
    "devils": "06_devils_advocate.md",
    "editor": "07_editor_in_chief.md",
    "architect": "08_format_architect.md",
    "builder": "09_html_builder.md",
    "judge-gemini": "10_judge_gemini.md",
    "judge-gpt": "11_judge_gpt.md",
    "judge-claude": "12_judge_claude.md",
}

# B3-S3-E: 에이전트 표시 메타 (이모지·색상 토큰). 프론트가 동일 토큰을 import 하므로
# 백엔드는 키 이름만 반환하고 색상 값은 프론트가 결정한다.
AGENT_DISPLAY: dict[str, dict[str, str]] = {
    "scout":        {"display_name": "Trend Scout",       "emoji": "🔍", "color_key": "scout"},
    "analyst":      {"display_name": "Audience Analyst",  "emoji": "👥", "color_key": "analyst"},
    "planner":      {"display_name": "Strategy Planner",  "emoji": "🎯", "color_key": "planner"},
    "writer":       {"display_name": "Writer",            "emoji": "✍️", "color_key": "writer"},
    "factchecker":  {"display_name": "Fact-Checker",      "emoji": "🔬", "color_key": "factchecker"},
    "devils":       {"display_name": "Devil's Advocate",  "emoji": "😈", "color_key": "devils"},
    "editor":       {"display_name": "Editor in Chief",   "emoji": "📝", "color_key": "editor"},
    "architect":    {"display_name": "Format Architect",  "emoji": "🏗️", "color_key": "architect"},
    "builder":      {"display_name": "HTML Builder",      "emoji": "🧱", "color_key": "builder"},
    "judge-gemini": {"display_name": "Judge · Gemini",    "emoji": "⚖️", "color_key": "judge-gemini"},
    "judge-gpt":    {"display_name": "Judge · GPT",       "emoji": "⚖️", "color_key": "judge-gpt"},
    "judge-claude": {"display_name": "Judge · Claude",    "emoji": "⚖️", "color_key": "judge-claude"},
}

_TS_FORMAT = "%Y%m%dT%H%M%S"
# 백업 파일명 패턴: "01_trend_scout_v3_20260605T120000.md"
_BACKUP_FILE_RE = re.compile(r"^(?P<stem>.+)_v(?P<v>\d+)_(?P<ts>\d{8}T\d{6})\.md$")


def _prompt_path(agent_id: str) -> Path:
    if agent_id not in AGENT_PROMPT_FILES:
        # 화이트리스트 검증 → traversal 차단
        raise HTTPException(status_code=404, detail=f"unknown agent_id: {agent_id}")
    return PROMPTS_DIR / AGENT_PROMPT_FILES[agent_id]


def _default_path(agent_id: str) -> Path:
    return DEFAULTS_DIR / AGENT_PROMPT_FILES[agent_id]


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _list_history_files(agent_id: str) -> list[Path]:
    if not VERSIONS_DIR.exists():
        return []
    stem = AGENT_PROMPT_FILES[agent_id].rsplit(".", 1)[0]
    files = list(VERSIONS_DIR.glob(f"{stem}_v*.md"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def _count_versions(agent_id: str) -> int:
    return len(_list_history_files(agent_id))


def _detect_variables(content: str) -> list[str]:
    """``{{TONE_REFERENCE}}`` 같은 변수 추출."""
    return sorted(set(re.findall(r"\{\{\s*([A-Z_][A-Z0-9_]*)\s*\}\}", content)))


def _estimate_tokens(content: str) -> int:
    """매우 거친 추정: 한국어 ≈ 2 chars / token."""
    return max(1, len(content) // 2)


def _backup_current(agent_id: str) -> str | None:
    """현재 파일을 ``.versions/`` 에 백업. 백업 파일명 반환 (없으면 None)."""
    path = _prompt_path(agent_id)
    if not path.exists():
        return None
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime(_TS_FORMAT)
    version_count = _count_versions(agent_id)
    stem, _, ext = AGENT_PROMPT_FILES[agent_id].rpartition(".")
    version_id = f"v{version_count + 1}"
    backup_path = VERSIONS_DIR / f"{stem}_{version_id}_{ts}.{ext}"
    backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return version_id


def _ensure_defaults_snapshot() -> None:
    """최초 부팅 시 1회: 현재 prompts/*.md 를 _defaults/ 에 복사.

    이후엔 _defaults 가 존재하는 한 skip — 진짜 ‘출고시 디폴트’ 의미.
    """
    DEFAULTS_DIR.mkdir(parents=True, exist_ok=True)
    for agent_id, filename in AGENT_PROMPT_FILES.items():
        src = PROMPTS_DIR / filename
        dst = DEFAULTS_DIR / filename
        if dst.exists():
            continue
        if not src.exists():
            logger.warning("prompt 원본 없음 — skip defaults snapshot: %s", src)
            continue
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info("default 스냅샷 생성: %s", dst.name)


# 모듈 import 시 1회 — uvicorn worker 1 개 기준 OK.
_ensure_defaults_snapshot()


# ---------------------------------------------------------------------
# 기존 B3-S3-A 엔드포인트 (호환 유지)
# ---------------------------------------------------------------------
@router.get("/prompts", response_model=PromptListResponse)
def list_prompts() -> PromptListResponse:
    out: list[PromptSummary] = []
    for agent_id, filename in AGENT_PROMPT_FILES.items():
        path = PROMPTS_DIR / filename
        if not path.exists():
            continue
        display = AGENT_DISPLAY.get(agent_id, {})
        out.append(
            PromptSummary(
                agent_id=agent_id,
                filename=filename,
                path=str(path.relative_to(PROJECT_ROOT).as_posix()),
                size_bytes=path.stat().st_size,
                last_modified=_file_mtime_iso(path),
                version_count=_count_versions(agent_id),
                display_name=display.get("display_name"),
                emoji=display.get("emoji"),
                color_key=display.get("color_key"),
            ),
        )
    return PromptListResponse(prompts=out)


@router.get("/prompts/{agent_id}", response_model=PromptDetail)
def get_prompt(agent_id: str) -> PromptDetail:
    path = _prompt_path(agent_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"파일 없음: {path}")
    content = path.read_text(encoding="utf-8")
    return PromptDetail(
        agent_id=agent_id,
        content=content,
        size_bytes=len(content.encode("utf-8")),
        last_modified=_file_mtime_iso(path),
        detected_variables=_detect_variables(content),
        estimated_tokens=_estimate_tokens(content),
    )


@router.put("/prompts/{agent_id}", response_model=PromptUpdateResponse)
def update_prompt(agent_id: str, body: PromptUpdate) -> PromptUpdateResponse:
    path = _prompt_path(agent_id)

    old_lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    new_lines = body.content.splitlines()
    added = max(0, len(new_lines) - len(old_lines))
    removed = max(0, len(old_lines) - len(new_lines))

    version_id: str | None = None
    if body.save_version:
        version_id = _backup_current(agent_id)

    path.write_text(body.content, encoding="utf-8")
    logger.info("prompt 저장: %s (version=%s, +%d/-%d)", agent_id, version_id, added, removed)

    return PromptUpdateResponse(
        agent_id=agent_id,
        saved_at=datetime.now(timezone.utc).isoformat(),
        size_bytes=len(body.content.encode("utf-8")),
        version_id=version_id,
        diff_summary=f"+{added} lines, -{removed} lines",
    )


# ---------------------------------------------------------------------
# B3-S3-E 신규 — restore / history / rollback
# ---------------------------------------------------------------------
@router.get("/prompts/{agent_id}/history", response_model=PromptHistoryResponse)
def get_prompt_history(agent_id: str) -> PromptHistoryResponse:
    _ = _prompt_path(agent_id)  # 화이트리스트 검증 부수효과
    out: list[PromptHistoryEntry] = []
    for fp in _list_history_files(agent_id):
        m = _BACKUP_FILE_RE.match(fp.name)
        if not m:
            continue
        out.append(
            PromptHistoryEntry(
                timestamp=m.group("ts"),
                version_id=f"v{m.group('v')}",
                filename=fp.name,
                size_bytes=fp.stat().st_size,
            )
        )
    return PromptHistoryResponse(agent_id=agent_id, history=out)


@router.post("/prompts/{agent_id}/restore", response_model=PromptRestoreResponse)
def restore_prompt(agent_id: str) -> PromptRestoreResponse:
    """``_defaults/`` 스냅샷으로 복원. 복원 직전 현재본은 history 백업."""
    path = _prompt_path(agent_id)
    default = _default_path(agent_id)
    if not default.exists():
        raise HTTPException(
            status_code=409,
            detail=f"기본값 스냅샷 없음: {default.name}",
        )

    _backup_current(agent_id)  # 안전망 — 복원 전 현재본 보존

    content = default.read_text(encoding="utf-8")
    path.write_text(content, encoding="utf-8")
    logger.info("prompt 기본값 복원: %s", agent_id)

    return PromptRestoreResponse(
        agent_id=agent_id,
        restored_from="defaults",
        saved_at=datetime.now(timezone.utc).isoformat(),
        size_bytes=len(content.encode("utf-8")),
    )


@router.post("/prompts/{agent_id}/rollback", response_model=PromptRestoreResponse)
def rollback_prompt(agent_id: str, body: PromptRollbackRequest) -> PromptRestoreResponse:
    """history 의 특정 timestamp 스냅샷으로 롤백."""
    _ = _prompt_path(agent_id)
    target: Path | None = None
    for fp in _list_history_files(agent_id):
        m = _BACKUP_FILE_RE.match(fp.name)
        if m and m.group("ts") == body.timestamp:
            target = fp
            break
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"timestamp {body.timestamp!r} 의 백업이 없습니다.",
        )

    _backup_current(agent_id)  # 롤백 전 현재본도 history 로 보존

    path = _prompt_path(agent_id)
    content = target.read_text(encoding="utf-8")
    path.write_text(content, encoding="utf-8")
    logger.info("prompt 롤백: %s ← %s", agent_id, target.name)

    return PromptRestoreResponse(
        agent_id=agent_id,
        restored_from=f"history:{body.timestamp}",
        saved_at=datetime.now(timezone.utc).isoformat(),
        size_bytes=len(content.encode("utf-8")),
    )

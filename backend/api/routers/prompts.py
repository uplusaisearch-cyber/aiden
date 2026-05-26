"""GET/PUT /api/prompts — 12 에이전트 system prompt CRUD."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.api.schemas.prompt import (
    PromptDetail,
    PromptListResponse,
    PromptSummary,
    PromptUpdate,
    PromptUpdateResponse,
)
from backend.core.settings import PROJECT_ROOT

router = APIRouter(prefix="/api", tags=["prompts"])

PROMPTS_DIR = PROJECT_ROOT / "backend" / "agents" / "prompts"
VERSIONS_DIR = PROMPTS_DIR / ".versions"

# agent_id ↔ 파일명 (B3-S3-A frontend agent id 와 동일)
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


def _prompt_path(agent_id: str) -> Path:
    if agent_id not in AGENT_PROMPT_FILES:
        raise HTTPException(status_code=404, detail=f"unknown agent_id: {agent_id}")
    return PROMPTS_DIR / AGENT_PROMPT_FILES[agent_id]


def _file_mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


def _count_versions(agent_id: str) -> int:
    if not VERSIONS_DIR.exists():
        return 0
    fname_stem = AGENT_PROMPT_FILES[agent_id].rsplit(".", 1)[0]
    return len(list(VERSIONS_DIR.glob(f"{fname_stem}_v*.md")))


def _detect_variables(content: str) -> list[str]:
    """``{{TONE_REFERENCE}}`` 같은 변수 추출."""
    return sorted(set(re.findall(r"\{\{\s*([A-Z_][A-Z0-9_]*)\s*\}\}", content)))


def _estimate_tokens(content: str) -> int:
    """매우 거친 추정: 한국어 ≈ 2 chars / token."""
    return max(1, len(content) // 2)


@router.get("/prompts", response_model=PromptListResponse)
def list_prompts() -> PromptListResponse:
    out: list[PromptSummary] = []
    for agent_id, filename in AGENT_PROMPT_FILES.items():
        path = PROMPTS_DIR / filename
        if not path.exists():
            continue
        out.append(
            PromptSummary(
                agent_id=agent_id,
                filename=filename,
                path=str(path.relative_to(PROJECT_ROOT).as_posix()),
                size_bytes=path.stat().st_size,
                last_modified=_file_mtime_iso(path),
                version_count=_count_versions(agent_id),
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
    if body.save_version and path.exists():
        VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        version_count = _count_versions(agent_id)
        stem, _, ext = AGENT_PROMPT_FILES[agent_id].rpartition(".")
        version_id = f"v{version_count + 1}"
        backup_path = VERSIONS_DIR / f"{stem}_{version_id}_{ts}.{ext}"
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

    path.write_text(body.content, encoding="utf-8")

    return PromptUpdateResponse(
        agent_id=agent_id,
        saved_at=datetime.now(timezone.utc).isoformat(),
        size_bytes=len(body.content.encode("utf-8")),
        version_id=version_id,
        diff_summary=f"+{added} lines, -{removed} lines",
    )

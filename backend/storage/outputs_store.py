"""종료된 run 의 결과 레코드만 영속 저장하는 SQLite 스토어.

명세: docs/patches/2026-06-05_output-history-persistence.md

설계 요지:
- 트레이스/대화/진행 중 run 은 저장 안 함. **완료 + final_html 있는 run** 만 1회 적재.
- 라이브 SSE 경로와 격리 — 적재 실패가 run 응답/이벤트를 깨지 않게 ``upsert_output`` 은 모든 예외를 삼키고 로그만 남김.
- DB 경로는 env ``OUTPUTS_DB_PATH`` 우선. 미설정 시 로컬 기본 ``backend/.cache/outputs.db``.
  Railway 배포에서는 Volume 마운트 경로(예: ``/data/outputs.db``)를 env 로 주입.
- 동시성: 매 호출 connection open/close + ``check_same_thread=False`` + ``threading.Lock`` 으로
  write 직렬화. SQLite 자체가 read 동시·write 직렬 모델이라 충분.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from backend.core.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH: Path = PROJECT_ROOT / "backend" / ".cache" / "outputs.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS outputs (
  run_id            TEXT PRIMARY KEY,
  topic             TEXT,
  category          TEXT,
  created_at        TEXT,
  weighted_score    REAL,
  scores_json       TEXT,
  total_tokens      INTEGER,
  total_cost_usd    REAL,
  cost_is_estimated INTEGER,
  final_html        TEXT
);
CREATE INDEX IF NOT EXISTS idx_outputs_created_at ON outputs(created_at DESC);
"""

_WRITE_LOCK = threading.Lock()


def get_db_path() -> Path:
    """env ``OUTPUTS_DB_PATH`` 우선, 미설정 시 로컬 기본 경로."""
    raw = os.environ.get("OUTPUTS_DB_PATH")
    return Path(raw) if raw else _DEFAULT_DB_PATH


def _connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """스키마 생성. 앱 기동 시 1회 호출. idempotent."""
    try:
        with _WRITE_LOCK, _connect() as conn:
            conn.executescript(_SCHEMA_SQL)
        logger.info("outputs.db init OK (path=%s)", get_db_path())
    except Exception as e:  # noqa: BLE001 — 기동 차단 금지
        logger.error("outputs.db init 실패 (path=%s): %s", get_db_path(), e)


def upsert_output(record: dict[str, Any]) -> None:
    """run 완료 시점 1회 호출. 동일 run_id 는 REPLACE.

    필수 키: run_id, final_html. 그 외는 NULL 허용.
    예외는 삼키고 log only — run 결과/SSE 와 격리.
    """
    run_id = record.get("run_id")
    if not run_id:
        logger.warning("upsert_output skip: run_id 없음")
        return
    if not record.get("final_html"):
        logger.info("upsert_output skip: final_html 없음 run_id=%s", run_id)
        return

    scores = record.get("scores_json")
    if isinstance(scores, (dict, list)):
        scores_text = json.dumps(scores, ensure_ascii=False)
    elif isinstance(scores, str) or scores is None:
        scores_text = scores
    else:
        scores_text = str(scores)

    cost_is_estimated = record.get("cost_is_estimated")
    if cost_is_estimated is not None:
        cost_is_estimated = 1 if cost_is_estimated else 0

    sql = (
        "INSERT OR REPLACE INTO outputs ("
        "run_id, topic, category, created_at, weighted_score, scores_json, "
        "total_tokens, total_cost_usd, cost_is_estimated, final_html"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    params = (
        run_id,
        record.get("topic"),
        record.get("category"),
        record.get("created_at"),
        record.get("weighted_score"),
        scores_text,
        record.get("total_tokens"),
        record.get("total_cost_usd"),
        cost_is_estimated,
        record["final_html"],
    )
    try:
        with _WRITE_LOCK, _connect() as conn:
            conn.execute(sql, params)
        logger.info("outputs.db upsert OK run_id=%s", run_id)
    except Exception as e:  # noqa: BLE001 — 적재 실패가 run 을 깨면 안 됨
        logger.error("outputs.db upsert 실패 run_id=%s: %s", run_id, e)


def _row_to_meta(row: sqlite3.Row) -> dict[str, Any]:
    """final_html 제외 메타 dict. scores_json 은 dict 로 파싱."""
    scores_raw = row["scores_json"]
    scores: Any = None
    if scores_raw:
        try:
            scores = json.loads(scores_raw)
        except (json.JSONDecodeError, TypeError):
            scores = None
    return {
        "run_id": row["run_id"],
        "topic": row["topic"],
        "category": row["category"],
        "created_at": row["created_at"],
        "weighted_score": row["weighted_score"],
        "scores": scores,
        "total_tokens": row["total_tokens"],
        "total_cost_usd": row["total_cost_usd"],
        "cost_is_estimated": bool(row["cost_is_estimated"]) if row["cost_is_estimated"] is not None else None,
    }


def list_outputs(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """final_html 제외 메타 리스트. created_at DESC."""
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT run_id, topic, category, created_at, weighted_score, scores_json, "
                "total_tokens, total_cost_usd, cost_is_estimated "
                "FROM outputs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            ).fetchall()
        return [_row_to_meta(r) for r in rows]
    except Exception as e:  # noqa: BLE001
        logger.error("outputs.db list 실패: %s", e)
        return []


def count_outputs() -> int:
    try:
        with _connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM outputs").fetchone()
        return int(row["n"]) if row else 0
    except Exception as e:  # noqa: BLE001
        logger.error("outputs.db count 실패: %s", e)
        return 0


def get_output(run_id: str) -> dict[str, Any] | None:
    """단건 + final_html 포함."""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT run_id, topic, category, created_at, weighted_score, scores_json, "
                "total_tokens, total_cost_usd, cost_is_estimated, final_html "
                "FROM outputs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        meta = _row_to_meta(row)
        meta["final_html"] = row["final_html"]
        return meta
    except Exception as e:  # noqa: BLE001
        logger.error("outputs.db get 실패 run_id=%s: %s", run_id, e)
        return None

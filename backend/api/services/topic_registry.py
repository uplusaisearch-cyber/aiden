"""발행 토픽 레지스트리 (Method A — JSON 파일).

명세: docs/patches/2026-06-04_b3-s3-e_admin_persona_ops.md §A3

- 저장 위치: ``data/topic_registry.json`` (PROJECT_ROOT 기준)
- ephemeral: 배포 컨테이너 재시작 시 소실. v2 에서 DB/Volume 으로.
- ``status == "published"`` + (``expiry`` null 또는 미래) 만 Topic Scout 에 주입.
"""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.core.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

REGISTRY_PATH = PROJECT_ROOT / "data" / "topic_registry.json"
_VALID_STATUS = {"published", "rejected", "expired"}
_VALID_CATEGORY = {"food", "ai_trend", "safety", "culture", "free"}


class TopicRegistry:
    """JSON 파일 기반 토픽 레지스트리.

    파일 IO 는 ``threading.Lock`` 으로 직렬화. 단일 worker 가정.
    """

    _instance: "TopicRegistry | None" = None
    _instance_lock = threading.Lock()

    def __init__(self, path: Path = REGISTRY_PATH) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._ensure_file()

    @classmethod
    def instance(cls) -> "TopicRegistry":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # 파일 IO
    # ------------------------------------------------------------------
    def _ensure_file(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else []
            if not isinstance(data, list):
                logger.warning("topic_registry.json 형식 오류 — 빈 목록으로 재초기화")
                return []
            return data
        except json.JSONDecodeError:
            logger.warning("topic_registry.json 파싱 실패 — 빈 목록")
            return []

    def _write(self, items: list[dict[str, Any]]) -> None:
        self._path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def list(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            items = self._read()
        if status:
            items = [i for i in items if i.get("status") == status]
        if category:
            items = [i for i in items if i.get("category") == category]
        # 최신순
        items.sort(key=lambda i: i.get("published_at") or "", reverse=True)
        return items

    def create(
        self,
        *,
        topic: str,
        category: str,
        status: str = "published",
        expiry: str | None = None,
        rejected_similar_to: str | None = None,
    ) -> dict[str, Any]:
        if status not in _VALID_STATUS:
            raise ValueError(f"unknown status: {status}")
        if category not in _VALID_CATEGORY:
            raise ValueError(f"unknown category: {category}")
        now = datetime.now(timezone.utc).isoformat()
        entry = {
            "id": str(uuid.uuid4()),
            "topic": topic.strip(),
            "category": category,
            "status": status,
            "published_at": now,
            "expiry": expiry,
            "rejected_similar_to": rejected_similar_to,
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            items = self._read()
            items.append(entry)
            self._write(items)
        logger.info("registry add: id=%s topic=%s status=%s", entry["id"], topic[:40], status)
        return entry

    def update(
        self,
        item_id: str,
        *,
        status: str | None = None,
        expiry: str | None = None,
        rejected_similar_to: str | None = None,
    ) -> dict[str, Any] | None:
        if status is not None and status not in _VALID_STATUS:
            raise ValueError(f"unknown status: {status}")
        with self._lock:
            items = self._read()
            target = next((i for i in items if i.get("id") == item_id), None)
            if target is None:
                return None
            if status is not None:
                target["status"] = status
            if expiry is not None:
                target["expiry"] = expiry or None
            if rejected_similar_to is not None:
                target["rejected_similar_to"] = rejected_similar_to or None
            target["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._write(items)
        return target

    def delete(self, item_id: str) -> bool:
        with self._lock:
            items = self._read()
            new_items = [i for i in items if i.get("id") != item_id]
            if len(new_items) == len(items):
                return False
            self._write(new_items)
        logger.info("registry delete: id=%s", item_id)
        return True

    # ------------------------------------------------------------------
    # Topic Scout 주입용
    # ------------------------------------------------------------------
    def published_active_topics(self) -> list[str]:
        """``status == published`` 이고 (expiry null 또는 미래)인 토픽 문자열 리스트."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._lock:
            items = self._read()
        out: list[str] = []
        for i in items:
            if i.get("status") != "published":
                continue
            expiry = i.get("expiry")
            if expiry and expiry < now_iso:
                continue
            t = i.get("topic")
            if isinstance(t, str) and t:
                out.append(t)
        return out


def render_published_topics_block() -> str:
    """Topic Scout system prompt 의 ``{{PUBLISHED_TOPICS}}`` 치환용 블록.

    리스트가 비어 있으면 ``(없음)`` 문자열을 반환해 prompt 안정성 유지.
    """
    topics = TopicRegistry.instance().published_active_topics()
    if not topics:
        return "(이미 발행된 토픽 없음)"
    lines = [f'- "{t}"' for t in topics]
    body = "\n".join(lines)
    return (
        "아래 목록은 이미 발행 완료된 토픽입니다. "
        "**중복·유사 주제는 회피하고 새로운 각도를 제안하세요.**\n"
        f"{body}"
    )

"""AIDEN 트레이스 로거.

각 에이전트 실행 결과를 runs/{run_id}/agents/*.json 으로 저장.
한 줄 요약은 runs/{run_id}/summary.jsonl 로 append.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TraceLogger:
    """실행당 1개 인스턴스. 모든 에이전트 결과를 단일 run 폴더에 저장.

    Usage:
        tracer = TraceLogger.new_run(base_dir="runs")
        tracer.log_agent_step(
            order=1,
            agent_name="trend_scout",
            iteration=None,
            input_data={...},
            output_data={...},
            duration_ms=2500,
        )
        tracer.write_metadata(user_input={...}, status="completed")
    """

    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.agents_dir = run_dir / "agents"
        self.summary_path = run_dir / "summary.jsonl"
        self.metadata_path = run_dir / "metadata.json"
        self.started_at = datetime.now(timezone.utc)
        self._step_count = 0

    @classmethod
    def new_run(cls, base_dir: str = "runs") -> "TraceLogger":
        """새 run 폴더 생성 후 TraceLogger 반환."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        run_id = f"{ts}_{uuid4().hex[:8]}"
        run_dir = Path(base_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "agents").mkdir(exist_ok=True)
        logger.info(f"New trace run started: {run_dir}")
        return cls(run_dir)

    def log_agent_step(
        self,
        order: int,
        agent_name: str,
        iteration: int | None,
        input_data: dict,
        output_data: dict,
        duration_ms: int,
        error: str | None = None,
    ) -> None:
        """에이전트 1회 실행 기록.

        Args:
            order: 실행 순서 (01, 02 ...). zero-padded 사용 권장.
            agent_name: snake_case (예: "trend_scout", "writer")
            iteration: Content Newsroom의 iter 번호 (없으면 None)
            input_data: 에이전트 입력 dict
            output_data: 에이전트 출력 dict
            duration_ms: 실행 소요 시간 (밀리초)
            error: 오류 발생 시 메시지
        """
        self._step_count += 1

        # 파일명: 01_trend_scout.json, 04_writer_iter1.json 등
        suffix = f"_iter{iteration}" if iteration is not None else ""
        filename = f"{order:02d}_{agent_name}{suffix}.json"
        filepath = self.agents_dir / filename

        record: dict[str, Any] = {
            "order": order,
            "agent_name": agent_name,
            "iteration": iteration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
            "input": input_data,
            "output": output_data,
            "error": error,
        }

        # 상세 기록
        try:
            filepath.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to write agent step: {e}")

        # 한 줄 요약
        summary = {
            "order": order,
            "agent": agent_name,
            "iteration": iteration,
            "duration_ms": duration_ms,
            "ok": error is None,
            "highlight": self._extract_highlight(agent_name, output_data),
        }
        try:
            with self.summary_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(summary, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write summary: {e}")

    @staticmethod
    def _extract_highlight(agent_name: str, output_data: dict) -> str:
        """에이전트별 한 줄 하이라이트 추출. 시각화용."""
        if not isinstance(output_data, dict):
            return ""

        # 에이전트별 핵심 필드 추출
        if agent_name == "trend_scout":
            topics = output_data.get("trending_topics", [])
            return f"3 topics: {', '.join(t.get('topic', '') for t in topics[:3])}"
        if agent_name == "audience_analyst":
            verdict = output_data.get("verdict", {})
            return f"top: {verdict.get('top_choice_topic', '')}"
        if agent_name == "strategy_planner":
            final = output_data.get("final_topic", {})
            return f"title: {final.get('title', '')}"
        # 기타 에이전트는 Step 3-2/3-3에서 추가
        return ""

    def write_metadata(
        self,
        user_input: dict,
        status: str,
        notes: str = "",
    ) -> None:
        """metadata.json 작성. run 종료 시 호출."""
        ended_at = datetime.now(timezone.utc)
        metadata = {
            "run_id": self.run_dir.name,
            "started_at": self.started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_sec": int((ended_at - self.started_at).total_seconds()),
            "user_input": user_input,
            "status": status,  # "completed" | "failed" | "partial"
            "step_count": self._step_count,
            "notes": notes,
        }
        try:
            self.metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to write metadata: {e}")

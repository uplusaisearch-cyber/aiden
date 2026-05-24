"""Topic Newsroom 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable 로 흐름 검증.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.orchestrators.topic_newsroom import TopicNewsroom
from backend.orchestrators.trace_logger import TraceLogger


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    """tmp_path 에 run 폴더 생성."""
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


def _scout_ok(_input: dict) -> dict:
    return {
        "category": _input["category"],
        "search_queries_used": ["test query"],
        "trending_topics": [
            {
                "topic": f"토픽 {i}",
                "why_trending": "테스트",
                "sources": [{"domain": "naver.com", "url": "https://...", "date": "2026-05"}],
                "estimated_volume": "medium",
                "longevity": "evergreen",
            }
            for i in range(3)
        ],
        "summary": "test summary",
    }


def _analyst_ok(_input: dict) -> dict:
    return {
        "category": _input["category"],
        "audience_evaluation": [
            {
                "topic": t["topic"],
                "fit_score": 8,
                "reasoning": "test",
                "concerns": "",
                "angle_suggestion": "test angle",
            }
            for t in _input["trending_topics"]
        ],
        "verdict": {
            "top_choice_topic": _input["trending_topics"][0]["topic"],
            "reasoning": "test",
        },
    }


def _planner_ok(_input: dict) -> dict:
    top = _input["audience_analyst"]["verdict"]["top_choice_topic"]
    return {
        "category": _input["category"],
        "deliberation": "test deliberation",
        "final_topic": {
            "category": _input["category"],
            "title": top,
            "angle": "test angle",
            "target_persona": "test persona",
            "content_type_recommendation": "A",
            "type_reasoning": "test",
            "estimated_read_time_min": 3,
            "key_messages": ["m1", "m2", "m3"],
            "data_grounding": [
                {
                    "fact": "test fact",
                    "source": {"domain": "naver.com", "url": "https://...", "date": "2026-05"},
                }
            ],
        },
        "rejected_topics": [
            {"topic": "토픽 1", "reason": "test"},
            {"topic": "토픽 2", "reason": "test"},
        ],
    }


# ---- Tests ------------------------------------------------------------------

class TestTopicNewsroom:

    def test_happy_path(self, tracer: TraceLogger) -> None:
        """3개 에이전트 모두 정상 → final_topic 반환."""
        tn = TopicNewsroom(tracer, _scout_ok, _analyst_ok, _planner_ok)
        result = tn.run(category="맛집")

        assert "final_topic" in result
        assert result["final_topic"]["category"] == "맛집"
        assert "title" in result["final_topic"]

    def test_trace_files_created(self, tracer: TraceLogger, tmp_path: Path) -> None:
        """트레이스 파일 3개 + summary.jsonl + metadata 가 생성됨."""
        tn = TopicNewsroom(tracer, _scout_ok, _analyst_ok, _planner_ok)
        tn.run(category="맛집")
        tracer.write_metadata(user_input={"category": "맛집"}, status="completed")

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("01_trend_scout" in f for f in files)
        assert any("02_audience_analyst" in f for f in files)
        assert any("03_strategy_planner" in f for f in files)

        # summary.jsonl 3줄
        lines = tracer.summary_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

        # metadata.json
        meta = json.loads(tracer.metadata_path.read_text(encoding="utf-8"))
        assert meta["status"] == "completed"
        assert meta["step_count"] == 3

    def test_analyst_input_excludes_summary(self, tracer: TraceLogger) -> None:
        """data_flow_spec §2-2: analyst 입력에 summary, search_queries_used 없어야 함."""
        captured_input: dict = {}

        def _analyst_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _analyst_ok(_input)

        tn = TopicNewsroom(tracer, _scout_ok, _analyst_capturing, _planner_ok)
        tn.run(category="맛집")

        assert "category" in captured_input
        assert "trending_topics" in captured_input
        assert "summary" not in captured_input
        assert "search_queries_used" not in captured_input

    def test_planner_receives_both_outputs(self, tracer: TraceLogger) -> None:
        """data_flow_spec §2-3: planner 입력에 trend_scout + audience_analyst 전체."""
        captured_input: dict = {}

        def _planner_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _planner_ok(_input)

        tn = TopicNewsroom(tracer, _scout_ok, _analyst_ok, _planner_capturing)
        tn.run(category="맛집")

        assert "trend_scout" in captured_input
        assert "audience_analyst" in captured_input
        assert "trending_topics" in captured_input["trend_scout"]
        assert "audience_evaluation" in captured_input["audience_analyst"]

    def test_scout_failure_returns_error(self, tracer: TraceLogger) -> None:
        """Trend Scout 실패 시 error 반환 (raise 안 함)."""
        def _scout_fail(_input: dict) -> dict:
            return {}  # trending_topics 없음

        tn = TopicNewsroom(tracer, _scout_fail, _analyst_ok, _planner_ok)
        result = tn.run(category="맛집")

        assert result.get("error") == "trend_scout_failed"

    def test_target_date_defaults_to_today(self, tracer: TraceLogger) -> None:
        """target_date 미전달 시 오늘 날짜 사용."""
        captured_input: dict = {}

        def _scout_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _scout_ok(_input)

        tn = TopicNewsroom(tracer, _scout_capturing, _analyst_ok, _planner_ok)
        tn.run(category="맛집")

        assert "target_date" in captured_input
        # ISO format YYYY-MM-DD
        assert len(captured_input["target_date"]) == 10
        assert captured_input["target_date"][4] == "-"

    def test_agent_exception_recorded_in_trace(self, tracer: TraceLogger) -> None:
        """에이전트가 예외 던져도 오케스트레이터는 raise 안 함, trace 에 기록."""
        def _scout_raise(_input: dict) -> dict:
            raise ValueError("simulated failure")

        tn = TopicNewsroom(tracer, _scout_raise, _analyst_ok, _planner_ok)
        result = tn.run(category="맛집")

        assert "error" in result

        # trace 파일에 error 기록 있어야 함
        scout_file = next(tracer.run_dir.glob("agents/01_trend_scout*.json"))
        scout_record = json.loads(scout_file.read_text(encoding="utf-8"))
        assert scout_record["error"] is not None
        assert "ValueError" in scout_record["error"]

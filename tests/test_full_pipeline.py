"""FullPipeline 통합 테스트.

실제 LLM 호출 없이 모의 9 에이전트 callable 로 전체 흐름 검증.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.orchestrators.full_pipeline import FullPipeline
from backend.orchestrators.trace_logger import TraceLogger


@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


def _scout(_input: dict) -> dict:
    return {
        "category": _input["category"],
        "search_queries_used": ["q"],
        "trending_topics": [
            {
                "topic": f"T{i}",
                "why_trending": "wt",
                "sources": [{"domain": "n.com", "url": "u", "date": "2026-05"}],
                "estimated_volume": "medium",
                "longevity": "evergreen",
            }
            for i in range(3)
        ],
        "summary": "s",
    }


def _analyst(_input: dict) -> dict:
    return {
        "category": _input["category"],
        "audience_evaluation": [
            {
                "topic": t["topic"],
                "fit_score": 8,
                "reasoning": "r",
                "concerns": "",
                "angle_suggestion": "a",
            }
            for t in _input["trending_topics"]
        ],
        "verdict": {"top_choice_topic": _input["trending_topics"][0]["topic"], "reasoning": "r"},
    }


def _planner(_input: dict) -> dict:
    top = _input["audience_analyst"]["verdict"]["top_choice_topic"]
    return {
        "category": _input["category"],
        "deliberation": "d",
        "final_topic": {
            "category": _input["category"],
            "title": top,
            "angle": "a",
            "target_persona": "p",
            "content_type_recommendation": "A",
            "type_reasoning": "tr",
            "estimated_read_time_min": 3,
            "key_messages": ["m1", "m2", "m3"],
            "data_grounding": [
                {
                    "fact": "f",
                    "source": {"domain": "n.com", "url": "u", "date": "2026-05"},
                }
            ],
        },
        "rejected_topics": [
            {"topic": "T1", "reason": "r"},
            {"topic": "T2", "reason": "r"},
        ],
    }


def _writer(_input: dict) -> dict:
    return {
        "draft_version": _input["iteration"],
        "category": _input["category"],
        "title": "WT",
        "subtitle": "WS",
        "intro": "WI",
        "sections": [
            {"heading": "h1", "body": "b1", "fact_claims": ["f1"]},
            {"heading": "h2", "body": "b2", "fact_claims": ["f2"]},
        ],
        "closing": "WC",
        "cta": "CT",
        "revision_notes": [] if _input["iteration"] == 1 else [{"target": "h1", "applied": "fixed"}],
    }


def _fc(_writer_draft: dict) -> dict:
    return {
        "verification_log": [
            {
                "claim": c,
                "status": "verified",
                "evidence": "e",
                "source_url": "u",
                "source_domain": "n.com",
                "source_date": "2026-05",
            }
            for s in _writer_draft["sections"] for c in s["fact_claims"]
        ],
        "annotated_draft": {
            "title": _writer_draft["title"],
            "subtitle": _writer_draft["subtitle"],
            "intro": _writer_draft["intro"],
            "sections": [
                {
                    "heading": s["heading"],
                    "body": s["body"] + " [출처: n.com, 2026-05]",
                    "fact_claims": [{"claim": c, "status": "verified"} for c in s["fact_claims"]],
                }
                for s in _writer_draft["sections"]
            ],
            "closing": _writer_draft["closing"],
            "cta": _writer_draft["cta"],
        },
        "confidence_score": 10,
        "summary": "all verified",
    }


def _da_pass(_input: dict) -> dict:
    iteration = _input["iteration"]
    return {
        "iteration": iteration,
        "overall_verdict": "ok",
        "scores": {
            "originality": 8,
            "reader_value": 8,
            "tone_authenticity": 8,
            "structure": 8,
            "title_hook": 8,
        },
        "critical_issues": [
            {"location": f"s{i}", "problem": "p", "suggestion": "s"}
            for i in range({1: 5, 2: 3, 3: 1}.get(iteration, 1))
        ],
        "pass_threshold": True,
        "carried_over_from_previous": [],
    }


def _editor_approved(_input: dict) -> dict:
    iteration = _input["iteration"]
    critique = _input["critique"]
    annotated = _input["factcheck"]["annotated_draft"]
    return {
        "iteration": iteration,
        "editorial_decision": "OK",
        "accepted_critiques": [
            {"issue": {"location": ci["location"], "problem": ci["problem"]}, "action": "직접 수정함"}
            for ci in critique["critical_issues"][:3]
        ],
        "rejected_critiques": [],
        "factcheck_handling": "ok",
        "decision": "approved",
        "final_content": {
            "category": _input["writer_draft"]["category"],
            "title": _input["writer_draft"]["title"],
            "subtitle": annotated.get("subtitle", ""),
            "intro": annotated.get("intro", ""),
            "sections": annotated["sections"],
            "closing": annotated.get("closing", ""),
            "cta": annotated.get("cta", ""),
            "sources": [{"domain": "n.com", "url": "u", "date": "2026-05"}],
            "known_weaknesses": [],
        },
    }


def _format_architect(_input: dict) -> dict:
    return {
        "format_analysis": "ok",
        "selected_type": "A",
        "base_layout": "A",
        "type_reasoning": "ok",
        "layout_hints": {"hero_image_needed": True, "image_count": 1, "image_descriptions": ["h"]},
        "placeholder_locations": [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ],
    }


def _html_builder(_input: dict) -> dict:
    return {
        "html": f"<article><h1>{_input['final_content']['title']}</h1></article>",
        "selected_type_applied": "A",
        "base_layout_used": "A",
        "interactive_template_used": None,
        "placeholder_substitutions": [],
        "preserved_placeholders": ["{{HERO_IMAGE_URL}}"],
        "warnings": [],
    }


@pytest.fixture
def agents() -> dict:
    return {
        "scout": _scout,
        "analyst": _analyst,
        "planner": _planner,
        "writer": _writer,
        "fact_checker": _fc,
        "devils_advocate": _da_pass,
        "editor": _editor_approved,
        "format_architect": _format_architect,
        "html_builder": _html_builder,
    }


class TestFullPipeline:

    def test_e2e_happy_path(self, tracer: TraceLogger, agents: dict) -> None:
        pipeline = FullPipeline(tracer=tracer, agents=agents)
        result = pipeline.run(category="맛집")

        assert result["status"] == "completed"
        assert "final_html" in result
        assert result["final_html"]  # not empty
        assert result["stage_1"]["final_topic"]["category"] == "맛집"
        assert result["stage_2"]["decision"] == "approved"
        assert result["stage_3"]["format_decision"]["selected_type"] == "A"

    def test_all_9_agents_traced(self, tracer: TraceLogger, agents: dict) -> None:
        pipeline = FullPipeline(tracer=tracer, agents=agents)
        pipeline.run(category="맛집")

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())

        # 01 ~ 09 모두 있어야 함 (iter 1만 종료된 경우)
        for prefix in [
            "01_trend_scout",
            "02_audience_analyst",
            "03_strategy_planner",
            "04_writer_iter1",
            "05_fact_checker_iter1",
            "06_devils_advocate_iter1",
            "07_editor_iter1",
            "08_format_architect",
            "09_html_builder",
        ]:
            assert any(prefix in f for f in files), f"Missing trace file: {prefix}"

    def test_missing_agent_raises(self, tracer: TraceLogger) -> None:
        incomplete = {"scout": _scout, "analyst": _analyst}  # 나머지 누락

        with pytest.raises(ValueError, match="누락"):
            FullPipeline(tracer=tracer, agents=incomplete)

    def test_stage_1_failure_short_circuits(
        self, tracer: TraceLogger, agents: dict
    ) -> None:
        def _scout_fail(_input: dict) -> dict:
            return {}

        bad_agents = {**agents, "scout": _scout_fail}
        pipeline = FullPipeline(tracer=tracer, agents=bad_agents)
        result = pipeline.run(category="맛집")

        assert result["status"] == "failed_stage_1"
        assert result["stage_2"] is None
        assert result["stage_3"] is None

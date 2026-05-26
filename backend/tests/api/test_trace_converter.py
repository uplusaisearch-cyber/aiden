"""trace_converter: raw agent_step → ChatMessage 변환 단위 테스트 (9건)."""
from __future__ import annotations

from backend.api.services.trace_converter import convert


def _wrap(agent_name: str, output: dict, iteration: int | None = None) -> dict:
    return {
        "order": 1,
        "agent_name": agent_name,
        "iteration": iteration,
        "timestamp": "2026-05-26T15:00:00+00:00",
        "duration_ms": 1500,
        "input": {},
        "output": output,
        "error": None,
        "highlight": "",
    }


class TestTraceConverter:
    def test_1_scout(self):
        out = {
            "trending_topics": [
                {"topic": "편의점 신상 디저트", "confidence": 0.92},
                {"topic": "여름 빙수 맛집"},
            ],
            "search_queries_used": ["q1", "q2", "q3"],
        }
        msgs = convert(_wrap("trend_scout", out))
        assert len(msgs) == 1
        m = msgs[0]
        assert m["agent_id"] == "scout"
        assert m["stage"] == 1
        assert "편의점 신상 디저트" in m["headline"]
        assert any(h["label"] == "검색 호출" for h in m["highlights"])
        assert any(b["label"] == "confidence" for b in m["badges"])

    def test_2_analyst(self):
        out = {"verdict": {"top_choice_topic": "편의점 디저트", "persona_fit_score": 0.85,
                            "reasoning": "30대 1인가구 적합"}}
        msgs = convert(_wrap("audience_analyst", out))
        assert msgs[0]["agent_id"] == "analyst"
        assert "편의점 디저트" in msgs[0]["headline"]

    def test_3_planner(self):
        out = {"final_topic": {"title": "편의점 디저트 베스트 7", "angle": "가성비",
                                "target_persona": "30대"}}
        msgs = convert(_wrap("strategy_planner", out))
        assert msgs[0]["agent_id"] == "planner"
        assert "편의점 디저트 베스트 7" in msgs[0]["headline"]

    def test_4_writer_iter1(self):
        out = {
            "title": "편의점 디저트 7선",
            "sections": [{"body": "본문" * 100}, {"body": "본문2"}],
            "draft_version": 1,
        }
        msgs = convert(_wrap("writer", out, iteration=1))
        assert msgs[0]["agent_id"] == "writer"
        assert "v1" in msgs[0]["headline"]
        assert msgs[0]["stage"] == 2

    def test_5_factchecker_verified_count(self):
        out = {
            "confidence_score": 8,
            "verification_log": [
                {"status": "verified"},
                {"status": "verified"},
                {"status": "unverified"},
            ],
            "summary": "검증 완료",
        }
        msgs = convert(_wrap("fact_checker", out, iteration=2))
        m = msgs[0]
        assert m["agent_id"] == "factchecker"
        assert "2/3" in m["headline"]
        assert any(b["color"] == "success" for b in m["badges"])

    def test_6_devils_pass_branch(self):
        out_pass = {
            "critical_issues": [{"issue": "출처 부족"}, {"issue": "구조 산만"}],
            "scores": {"a": 7, "b": 6, "c": 6.5},
            "pass_threshold": True,
        }
        m_pass = convert(_wrap("devils_advocate", out_pass))[0]
        assert any(b["value"] == "통과" for b in m_pass["badges"])

        out_fail = {**out_pass, "pass_threshold": False}
        m_fail = convert(_wrap("devils_advocate", out_fail))[0]
        assert any(b["value"] == "재작성" for b in m_fail["badges"])

    def test_7_editor_decision_branch(self):
        for decision, label in [("approved", "승인"), ("needs_revision", "재작성")]:
            out = {
                "decision": decision,
                "accepted_critiques": [{"id": 1}, {"id": 2}],
                "rejected_critiques": [{"id": 3}],
            }
            m = convert(_wrap("editor", out, iteration=2))[0]
            assert label in m["headline"]
            assert any(b["value"] == label for b in m["badges"])

    def test_8_html_builder(self):
        out = {
            "selected_type_applied": "B",
            "placeholder_substitutions": [1, 2, 3],
            "preserved_placeholders": [],
            "warnings": ["warn1"],
        }
        m = convert(_wrap("html_builder", out))[0]
        assert m["agent_id"] == "builder"
        assert m["stage"] == 3
        assert any(b["label"] == "warnings" for b in m["badges"])

    def test_9_judge_panel_three_messages(self):
        """judge_panel 입력 1개 → message 3개 (gemini/gpt/claude)."""
        out = {
            "status": "completed",
            "evaluations": {
                "gemini": {
                    "scores": {"topic_fit": 8, "content_quality": 7, "interactivity": 9,
                               "tone_authenticity": 6, "timeliness_trust": 7},
                    "overall_score": 7.4,
                    "one_line_verdict": "주제 좋음",
                    "strengths": ["a", "b"],
                    "weaknesses": ["c"],
                },
                "gpt": {
                    "scores": {"topic_fit": 7, "content_quality": 6, "interactivity": 8,
                               "tone_authenticity": 6, "timeliness_trust": 7},
                    "overall_score": 6.8,
                    "one_line_verdict": "균형",
                    "strengths": ["a"],
                    "weaknesses": ["b"],
                },
                "claude": {
                    "scores": {"topic_fit": 7, "content_quality": 7, "interactivity": 8,
                               "tone_authenticity": 5, "timeliness_trust": 6},
                    "overall_score": 6.6,
                    "one_line_verdict": "엄격",
                    "strengths": ["a"],
                    "weaknesses": ["b", "c"],
                },
            },
        }
        msgs = convert(_wrap("judge_panel", out))
        assert len(msgs) == 3
        ids = {m["agent_id"] for m in msgs}
        assert ids == {"judge-gemini", "judge-gpt", "judge-claude"}
        for m in msgs:
            assert m["stage"] == 4
            assert m["headline"].startswith("⭐")
            assert any(b["label"] == "overall" for b in m["badges"])

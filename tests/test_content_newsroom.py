"""Content Newsroom 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable 로 흐름 검증.
- iter 1에서 approved 즉시 종료
- iter 2에서 approved
- iter 3 강제 종료
- 에이전트 실패 시 강제 approved
- 입력 조립 규칙 (data_flow_spec §4-2)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from backend.orchestrators.content_newsroom import ContentNewsroom
from backend.orchestrators.trace_logger import TraceLogger


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


@pytest.fixture
def strategy() -> dict:
    return {
        "category": "맛집",
        "title": "테스트 가제목",
        "angle": "테스트 앵글",
        "target_persona": "30대 직장인",
        "content_type_recommendation": "A",
        "type_reasoning": "test",
        "estimated_read_time_min": 3,
        "key_messages": ["m1", "m2", "m3"],
        "data_grounding": [
            {"fact": "test", "source": {"domain": "naver.com", "url": "...", "date": "2026-05"}}
        ],
    }


def _writer_ok(_input: dict) -> dict:
    return {
        "draft_version": _input["iteration"],
        "category": _input["category"],
        "title": "Writer 제목",
        "subtitle": "부제",
        "intro": "도입",
        "sections": [
            {"heading": "s1", "body": "본문 1", "fact_claims": ["fact A"]},
            {"heading": "s2", "body": "본문 2", "fact_claims": ["fact B"]},
        ],
        "closing": "마무리",
        "cta": "CTA",
        "revision_notes": [] if _input["iteration"] == 1 else [{"target": "s1", "applied": "수정함"}],
    }


def _fc_ok(_writer_draft: dict) -> dict:
    return {
        "verification_log": [
            {
                "claim": "fact A",
                "status": "verified",
                "evidence": "...",
                "source_url": "...",
                "source_domain": "naver.com",
                "source_date": "2026-05",
            },
            {
                "claim": "fact B",
                "status": "verified",
                "evidence": "...",
                "source_url": "...",
                "source_domain": "naver.com",
                "source_date": "2026-05",
            },
        ],
        "annotated_draft": {
            "title": _writer_draft["title"],
            "subtitle": _writer_draft["subtitle"],
            "intro": _writer_draft["intro"],
            "sections": [
                {**s, "fact_claims": [{"claim": c, "status": "verified"} for c in s["fact_claims"]]}
                for s in _writer_draft["sections"]
            ],
            "closing": _writer_draft["closing"],
            "cta": _writer_draft["cta"],
        },
        "confidence_score": 9,
        "summary": "모두 검증됨",
    }


def _da_pass(_input: dict) -> dict:
    """DA 가 pass_threshold=True 반환 (iter 1에서 종료 유도)."""
    iteration = _input["iteration"]
    count_map = {1: 5, 2: 3, 3: 1}
    n = count_map.get(iteration, 1)
    return {
        "iteration": iteration,
        "overall_verdict": "OK",
        "scores": {
            "originality": 8,
            "reader_value": 8,
            "tone_authenticity": 8,
            "structure": 8,
            "title_hook": 8,
        },
        "critical_issues": [
            {"location": f"section {i}", "problem": f"문제 {i}", "suggestion": f"제안 {i}"}
            for i in range(n)
        ],
        "pass_threshold": True,
        "carried_over_from_previous": [] if iteration == 1 else [],
    }


def _da_fail(_input: dict) -> dict:
    """DA 가 pass_threshold=False 반환 (재작성 유도)."""
    iteration = _input["iteration"]
    count_map = {1: 5, 2: 3, 3: 1}
    n = count_map.get(iteration, 1)
    return {
        "iteration": iteration,
        "overall_verdict": "Bad",
        "scores": {
            "originality": 4,
            "reader_value": 4,
            "tone_authenticity": 4,
            "structure": 4,
            "title_hook": 4,
        },
        "critical_issues": [
            {"location": f"section {i}", "problem": f"문제 {i}", "suggestion": f"제안 {i}"}
            for i in range(n)
        ],
        "pass_threshold": False,
        "carried_over_from_previous": [],
    }


def _editor_approved(_input: dict) -> dict:
    iteration = _input["iteration"]
    critique = _input["critique"]
    return {
        "iteration": iteration,
        "editorial_decision": "승인",
        "accepted_critiques": [
            {"issue": {"location": ci["location"], "problem": ci["problem"]}, "action": "직접 수정함"}
            for ci in critique["critical_issues"][:3]
        ],
        "rejected_critiques": [],
        "factcheck_handling": "양호",
        "decision": "approved",
        "final_content": {
            "category": _input["writer_draft"]["category"],
            "title": _input["writer_draft"]["title"],
            "subtitle": _input["writer_draft"]["subtitle"],
            "intro": _input["writer_draft"]["intro"],
            "sections": _input["factcheck"]["annotated_draft"]["sections"],
            "closing": _input["writer_draft"]["closing"],
            "cta": _input["writer_draft"]["cta"],
            "sources": [{"domain": "naver.com", "url": "...", "date": "2026-05"}],
            "known_weaknesses": [],
        },
    }


def _editor_needs_revision(_input: dict) -> dict:
    iteration = _input["iteration"]
    return {
        "iteration": iteration,
        "editorial_decision": "재작성 필요",
        "accepted_critiques": [],
        "rejected_critiques": [],
        "factcheck_handling": "보통",
        "decision": "needs_revision",
        "revision_instructions": [
            {"target": "section 1", "instruction": "구체화"},
            {"target": "intro", "instruction": "후킹 강화"},
        ],
    }


# ---- Tests ------------------------------------------------------------------

class TestContentNewsroomHappyPath:

    def test_iter1_approved_immediately(self, tracer: TraceLogger, strategy: dict) -> None:
        """iter 1 에서 Editor approved → 즉시 종료."""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)

        assert result["decision"] == "approved"
        assert result["iteration"] == 1
        assert "final_content" in result

    def test_iter2_approved_after_revision(self, tracer: TraceLogger, strategy: dict) -> None:
        """iter 1 fail → iter 2 approved."""
        call_counter = {"editor": 0}

        def _editor_iter2(_input: dict) -> dict:
            call_counter["editor"] += 1
            if call_counter["editor"] == 1:
                return _editor_needs_revision(_input)
            return _editor_approved(_input)

        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_iter2)
        result = cn.run(category="맛집", strategy=strategy)

        assert result["decision"] == "approved"
        assert result["iteration"] == 2


class TestContentNewsroomForceTermination:

    def test_iter3_force_approved_when_editor_says_needs_revision(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """iter 3에서 Editor 가 needs_revision 반환해도 오케스트레이터가 approved 강제."""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_fail, _editor_needs_revision)
        result = cn.run(category="맛집", strategy=strategy)

        assert result["decision"] == "approved"  # 강제됨
        assert result.get("_orchestrator_coerced_at_iter3") is True
        assert "known_weaknesses" in result["final_content"]
        assert len(result["final_content"]["known_weaknesses"]) > 0


class TestContentNewsroomAgentFailure:

    def test_writer_fails_iter1_force_approved(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """Writer 실패 시 강제 approved (raise 안 함)."""
        def _writer_fail(_input: dict) -> dict:
            return {}  # sections 없음

        cn = ContentNewsroom(tracer, _writer_fail, _fc_ok, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)

        assert result["decision"] == "approved"
        assert result.get("_orchestrator_forced") is True
        assert "writer_failed" in result.get("_force_reason", "")

    def test_fc_raises_exception_force_approved(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """Fact-Checker 가 예외 던져도 raise 안 함."""
        def _fc_raise(_input: dict) -> dict:
            raise RuntimeError("FC down")

        cn = ContentNewsroom(tracer, _writer_ok, _fc_raise, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)

        assert result["decision"] == "approved"
        assert result.get("_orchestrator_forced") is True


class TestContentNewsroomInputAssembly:

    def test_writer_iter1_input_no_previous(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """iter 1 Writer 입력에 previous_draft 등 없음."""
        captured: list[dict] = []

        def _writer_capturing(_input: dict) -> dict:
            captured.append(dict(_input))
            return _writer_ok(_input)

        cn = ContentNewsroom(tracer, _writer_capturing, _fc_ok, _da_pass, _editor_approved)
        cn.run(category="맛집", strategy=strategy)

        first_call = captured[0]
        assert first_call["iteration"] == 1
        assert first_call["category"] == "맛집"
        assert "strategy" in first_call
        assert "previous_draft" not in first_call
        assert "editor_instructions" not in first_call

    def test_writer_iter2_input_has_previous(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """iter 2 Writer 입력에 previous_draft, factcheck_log, critique, editor_instructions 모두 포함."""
        captured: list[dict] = []

        def _writer_capturing(_input: dict) -> dict:
            captured.append(dict(_input))
            return _writer_ok(_input)

        call_counter = {"editor": 0}

        def _editor_two_iters(_input: dict) -> dict:
            call_counter["editor"] += 1
            if call_counter["editor"] == 1:
                return _editor_needs_revision(_input)
            return _editor_approved(_input)

        cn = ContentNewsroom(
            tracer, _writer_capturing, _fc_ok, _da_pass, _editor_two_iters
        )
        cn.run(category="맛집", strategy=strategy)

        assert len(captured) >= 2
        second_call = captured[1]
        assert second_call["iteration"] == 2
        assert "previous_draft" in second_call
        assert "factcheck_log" in second_call
        assert "critique" in second_call
        assert "editor_instructions" in second_call
        # editor_instructions 는 needs_revision 의 revision_instructions 를 그대로 받음
        assert isinstance(second_call["editor_instructions"], list)

    def test_da_iter2_input_has_previous_critiques(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """iter 2 DA 입력에 previous_critiques + editor_response."""
        captured: list[dict] = []

        def _da_capturing(_input: dict) -> dict:
            captured.append(dict(_input))
            return _da_pass(_input)

        call_counter = {"editor": 0}

        def _editor_two_iters(_input: dict) -> dict:
            call_counter["editor"] += 1
            if call_counter["editor"] == 1:
                return _editor_needs_revision(_input)
            return _editor_approved(_input)

        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_capturing, _editor_two_iters)
        cn.run(category="맛집", strategy=strategy)

        assert len(captured) >= 2
        second_call = captured[1]
        assert "previous_critiques" in second_call
        assert "editor_response" in second_call
        assert "accepted_critiques" in second_call["editor_response"]
        assert "rejected_critiques" in second_call["editor_response"]


class TestContentNewsroomTraceLogging:

    def test_trace_files_include_iteration_suffix(
        self, tracer: TraceLogger, strategy: dict
    ) -> None:
        """iter 1 에서 종료 시 04_writer_iter1.json 등 파일 생성."""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_approved)
        cn.run(category="맛집", strategy=strategy)

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("04_writer_iter1" in f for f in files)
        assert any("05_fact_checker_iter1" in f for f in files)
        assert any("06_devils_advocate_iter1" in f for f in files)
        assert any("07_editor_iter1" in f for f in files)

    def test_trace_multi_iter(self, tracer: TraceLogger, strategy: dict) -> None:
        """iter 2 종료 시 iter1, iter2 파일 모두 생성."""
        call_counter = {"editor": 0}

        def _editor_two_iters(_input: dict) -> dict:
            call_counter["editor"] += 1
            if call_counter["editor"] == 1:
                return _editor_needs_revision(_input)
            return _editor_approved(_input)

        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_two_iters)
        cn.run(category="맛집", strategy=strategy)

        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())

        # iter 1 + iter 2 각 4개씩 = 8개 이상
        iter1_count = sum(1 for f in files if "iter1" in f)
        iter2_count = sum(1 for f in files if "iter2" in f)
        assert iter1_count == 4
        assert iter2_count == 4

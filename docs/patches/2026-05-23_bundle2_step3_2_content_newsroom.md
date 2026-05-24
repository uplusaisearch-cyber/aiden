# 묶음 2 Step 3-2 작업 명세서 — Content Newsroom 오케스트레이터

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2의 Step 3-2  
**범위**: Content Newsroom (iter 1/2/3 토론) + TraceLogger 하이라이트 확장 + 단위 테스트  
**실행 방식**: 코드 작성 + pytest 단위 테스트 실행

---

## Step 3 분할 진행 상태

| Step | 작업 | 상태 |
|---|---|---|
| Step 3-1 | data_flow_spec + 트레이스 로깅 + Topic Newsroom | ✅ 완료 |
| **Step 3-2 (이번)** | Content Newsroom (iter 1/2/3, Writer ↔ FC ↔ DA ↔ Editor) | ✅ |
| Step 3-3 | Game-ifier (Format Architect → HTML Builder) + 전체 통합 | 다음 |

---

## 본 명세서 작업 개요

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `backend/orchestrators/content_newsroom.py` | 신규 |
| 2 | `backend/orchestrators/trace_logger.py` | 패치 (highlight 4종 추가) |
| 3 | `backend/orchestrators/__init__.py` | 패치 (ContentNewsroom export) |
| 4 | `tests/test_content_newsroom.py` | 신규 (단위 테스트) |
| 5 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 |

---

## 설계 결정사항 (사용자 확정)

| # | 결정 | 영향 |
|---|---|---|
| 1 | DeprecationWarning 패치 | Step 3-1 별도 처리 완료 |
| 2 | **종료 출력: Editor 전체** | `editor_output_v_final` 반환. final_content는 호출자가 추출. |
| 3 | **에이전트 실패 시 강제 approved** | partial 결과로라도 final_content 구성, trace에 fail 명시 |
| 4 | **FC 위치: 매 iter 재실행** | 정확도 우선. Editor confidence_score ≤6 트리거가 동작하려면 매 iter 필수. |

---

# 작업 1: backend/orchestrators/content_newsroom.py 신규

Content Newsroom 오케스트레이터. Stage 2. 가장 복잡.

```python
"""
Content Newsroom (Stage 2).

흐름: 최대 3 iter 토론
  iter N: Writer → Fact-Checker → Devil's Advocate → Editor
종료 조건:
  - editor.decision == "approved" → 즉시 종료
  - iter == 3 AND decision == "needs_revision" → 강제 종료 (Editor가 known_weaknesses 포함)

데이터 흐름은 docs/architecture/data_flow_spec.md §4 참조.
"""
from __future__ import annotations

import logging
from typing import Callable

from .base_newsroom import BaseNewsroom

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
DA_CRITICAL_COUNT_BY_ITER = {1: 5, 2: 3, 3: 1}  # 참고용 (prompt에 박혀있음)


class ContentNewsroom(BaseNewsroom):
    """
    Stage 2: Strategy Planner의 final_topic으로부터 final_content 도출.
    
    Usage:
        cn = ContentNewsroom(
            tracer=tracer,
            writer_fn=writer_callable,
            fact_checker_fn=fact_checker_callable,
            devils_advocate_fn=da_callable,
            editor_fn=editor_callable,
            base_order=4,  # Topic Newsroom이 1-3 차지했으므로 4부터
        )
        result = cn.run(category="맛집", strategy=planner_output["final_topic"])
    """
    
    def __init__(
        self,
        tracer,
        writer_fn: Callable[[dict], dict],
        fact_checker_fn: Callable[[dict], dict],
        devils_advocate_fn: Callable[[dict], dict],
        editor_fn: Callable[[dict], dict],
        base_order: int = 4,
    ):
        super().__init__(tracer)
        self.writer_fn = writer_fn
        self.fact_checker_fn = fact_checker_fn
        self.devils_advocate_fn = devils_advocate_fn
        self.editor_fn = editor_fn
        self.base_order = base_order
    
    def run(self, category: str, strategy: dict) -> dict:
        """
        Content Newsroom 실행.
        
        Args:
            category: 카테고리 (Writer 입력의 최상위 필드)
            strategy: Strategy Planner의 final_topic 객체 그대로
        
        Returns:
            Editor의 최종 출력 (decision="approved" 보장).
            모든 에이전트 실패 시에도 partial dict 반환 (raise 안 함).
        """
        writer_output: dict = {}
        factcheck_output: dict = {}
        da_output: dict = {}
        editor_output: dict = {}
        
        for iteration in range(1, MAX_ITERATIONS + 1):
            logger.info(f"Content Newsroom iter {iteration} start")
            
            # ---- Writer ----
            writer_input = self._build_writer_input(
                iteration=iteration,
                category=category,
                strategy=strategy,
                previous_draft=writer_output,
                factcheck_log=factcheck_output,
                critique=da_output,
                editor_output=editor_output,
            )
            writer_output, writer_err = self._execute_agent(
                order=self.base_order,
                agent_name="writer",
                agent_callable=self.writer_fn,
                input_data=writer_input,
                iteration=iteration,
            )
            if writer_err or not writer_output.get("sections"):
                logger.error(f"Writer failed at iter {iteration}: {writer_err}")
                return self._force_approve(
                    iteration=iteration,
                    writer_output=writer_output,
                    factcheck_output=factcheck_output,
                    da_output=da_output,
                    fail_reason=f"writer_failed_iter{iteration}: {writer_err}",
                )
            
            # ---- Fact-Checker ----
            factcheck_output, fc_err = self._execute_agent(
                order=self.base_order + 1,
                agent_name="fact_checker",
                agent_callable=self.fact_checker_fn,
                input_data=writer_output,
                iteration=iteration,
            )
            if fc_err or not factcheck_output.get("annotated_draft"):
                logger.error(f"Fact-Checker failed at iter {iteration}: {fc_err}")
                return self._force_approve(
                    iteration=iteration,
                    writer_output=writer_output,
                    factcheck_output=factcheck_output,
                    da_output=da_output,
                    fail_reason=f"fact_checker_failed_iter{iteration}: {fc_err}",
                )
            
            # ---- Devil's Advocate ----
            da_input = self._build_da_input(
                iteration=iteration,
                category=category,
                annotated_draft=factcheck_output["annotated_draft"],
                previous_da_output=da_output,
                previous_editor_output=editor_output,
            )
            da_output, da_err = self._execute_agent(
                order=self.base_order + 2,
                agent_name="devils_advocate",
                agent_callable=self.devils_advocate_fn,
                input_data=da_input,
                iteration=iteration,
            )
            if da_err or "critical_issues" not in da_output:
                logger.error(f"Devil's Advocate failed at iter {iteration}: {da_err}")
                return self._force_approve(
                    iteration=iteration,
                    writer_output=writer_output,
                    factcheck_output=factcheck_output,
                    da_output=da_output,
                    fail_reason=f"da_failed_iter{iteration}: {da_err}",
                )
            
            # ---- Editor ----
            editor_input = {
                "iteration": iteration,
                "writer_draft": writer_output,
                "factcheck": factcheck_output,
                "critique": da_output,
            }
            editor_output, editor_err = self._execute_agent(
                order=self.base_order + 3,
                agent_name="editor",
                agent_callable=self.editor_fn,
                input_data=editor_input,
                iteration=iteration,
            )
            if editor_err or not editor_output.get("decision"):
                logger.error(f"Editor failed at iter {iteration}: {editor_err}")
                return self._force_approve(
                    iteration=iteration,
                    writer_output=writer_output,
                    factcheck_output=factcheck_output,
                    da_output=da_output,
                    fail_reason=f"editor_failed_iter{iteration}: {editor_err}",
                )
            
            # ---- 종료 조건 ----
            if editor_output["decision"] == "approved":
                logger.info(f"Content Newsroom approved at iter {iteration}")
                return editor_output
            
            if iteration == MAX_ITERATIONS:
                # iter 3에서 needs_revision이면 Editor가 prompt 규칙대로 approved로 강제 종료해야 하지만,
                # 만약 안 그랬다면 오케스트레이터가 한 번 더 보장.
                logger.warning(
                    f"Editor returned needs_revision at iter 3. Forcing approved with known_weaknesses."
                )
                return self._coerce_approved_at_iter3(editor_output, da_output, factcheck_output)
        
        # 이론상 도달 불가 (for 루프가 iter 3에서 무조건 return)
        return editor_output
    
    def _build_writer_input(
        self,
        iteration: int,
        category: str,
        strategy: dict,
        previous_draft: dict,
        factcheck_log: dict,
        critique: dict,
        editor_output: dict,
    ) -> dict:
        """data_flow_spec §4-2 Writer 입력 조립."""
        base = {
            "iteration": iteration,
            "category": category,
            "strategy": strategy,
        }
        if iteration >= 2:
            base["previous_draft"] = previous_draft
            base["factcheck_log"] = factcheck_log
            base["critique"] = critique
            # editor.revision_instructions를 Writer가 그대로 사용
            base["editor_instructions"] = editor_output.get("revision_instructions", [])
        return base
    
    def _build_da_input(
        self,
        iteration: int,
        category: str,
        annotated_draft: dict,
        previous_da_output: dict,
        previous_editor_output: dict,
    ) -> dict:
        """data_flow_spec §4-2 Devil's Advocate 입력 조립."""
        base = {
            "iteration": iteration,
            "category": category,
            "annotated_draft": annotated_draft,
        }
        if iteration >= 2:
            base["previous_critiques"] = previous_da_output.get("critical_issues", [])
            base["editor_response"] = {
                "accepted_critiques": previous_editor_output.get("accepted_critiques", []),
                "rejected_critiques": previous_editor_output.get("rejected_critiques", []),
            }
        return base
    
    def _force_approve(
        self,
        iteration: int,
        writer_output: dict,
        factcheck_output: dict,
        da_output: dict,
        fail_reason: str,
    ) -> dict:
        """
        에이전트 실패 시 강제 approved (사용자 결정 #3).
        partial 결과로라도 final_content 구성. trace에 fail 명시는 이미 _execute_agent에서 됨.
        """
        logger.warning(f"Force-approving due to failure: {fail_reason}")
        
        # annotated_draft가 있으면 그걸, 없으면 writer_output을 base로
        base_content = factcheck_output.get("annotated_draft") or writer_output
        
        return {
            "iteration": iteration,
            "editorial_decision": (
                f"강제 종료: 에이전트 실패로 partial 결과 채택. 사유: {fail_reason}"
            ),
            "accepted_critiques": [],
            "rejected_critiques": [],
            "factcheck_handling": "강제 종료로 검증 미완료",
            "decision": "approved",
            "final_content": {
                "category": writer_output.get("category", ""),
                "title": base_content.get("title", "(제목 미생성)"),
                "subtitle": base_content.get("subtitle", ""),
                "intro": base_content.get("intro", ""),
                "sections": base_content.get("sections", []),
                "closing": base_content.get("closing", ""),
                "cta": base_content.get("cta", ""),
                "sources": [],
                "known_weaknesses": [
                    f"강제 종료 사유: {fail_reason}",
                    "Devil's Advocate 미반영 비판: "
                    + str(da_output.get("critical_issues", [])),
                ],
            },
            "_orchestrator_forced": True,
            "_force_reason": fail_reason,
        }
    
    def _coerce_approved_at_iter3(
        self,
        editor_output: dict,
        da_output: dict,
        factcheck_output: dict,
    ) -> dict:
        """
        iter 3에서 Editor가 needs_revision으로 끝낸 경우 prompt 규칙 위반.
        오케스트레이터가 한 번 더 보장: approved + known_weaknesses 채움.
        """
        coerced = dict(editor_output)
        coerced["decision"] = "approved"
        
        # final_content가 없으면 최소 골격 구성
        if "final_content" not in coerced or not coerced["final_content"]:
            annotated = factcheck_output.get("annotated_draft", {})
            coerced["final_content"] = {
                "category": annotated.get("category", ""),
                "title": annotated.get("title", "(제목 미생성)"),
                "subtitle": annotated.get("subtitle", ""),
                "intro": annotated.get("intro", ""),
                "sections": annotated.get("sections", []),
                "closing": annotated.get("closing", ""),
                "cta": annotated.get("cta", ""),
                "sources": [],
                "known_weaknesses": [],
            }
        
        # known_weaknesses 보강
        known = coerced["final_content"].get("known_weaknesses", []) or []
        if da_output.get("critical_issues"):
            known.append(
                f"iter 3 DA 잔여 비판: {da_output['critical_issues']}"
            )
        if factcheck_output.get("confidence_score", 10) <= 6:
            known.append(
                f"Fact-Checker confidence_score 낮음: {factcheck_output.get('confidence_score')}"
            )
        coerced["final_content"]["known_weaknesses"] = known
        coerced["_orchestrator_coerced_at_iter3"] = True
        
        return coerced
```

---

# 작업 2: backend/orchestrators/trace_logger.py 패치

`_extract_highlight` 메서드에 Writer / Fact-Checker / Devil's Advocate / Editor 4종 추가.

## 2-1. _extract_highlight 메서드 교체

### BEFORE

````python
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
````

### AFTER

````python
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
        if agent_name == "writer":
            title = output_data.get("title", "")
            sections = output_data.get("sections", [])
            return f"draft v{output_data.get('draft_version', '?')}: '{title}' ({len(sections)} sections)"
        if agent_name == "fact_checker":
            score = output_data.get("confidence_score", "?")
            log = output_data.get("verification_log", [])
            verified = sum(1 for x in log if x.get("status") == "verified")
            return f"confidence={score}, verified={verified}/{len(log)}"
        if agent_name == "devils_advocate":
            issues = output_data.get("critical_issues", [])
            scores = output_data.get("scores", {})
            avg = sum(scores.values()) / len(scores) if scores else 0
            return f"{len(issues)} critiques, avg score={avg:.1f}, pass={output_data.get('pass_threshold', False)}"
        if agent_name == "editor":
            decision = output_data.get("decision", "?")
            accepted = len(output_data.get("accepted_critiques", []))
            rejected = len(output_data.get("rejected_critiques", []))
            return f"decision={decision}, accepted={accepted}, rejected={rejected}"
        # 기타 에이전트는 Step 3-3에서 추가
        return ""
````

---

# 작업 3: backend/orchestrators/__init__.py 패치

ContentNewsroom export 추가.

### BEFORE

````python
"""AIDEN 오케스트레이터 패키지."""
from .trace_logger import TraceLogger
from .base_newsroom import BaseNewsroom, AgentExecutionError
from .topic_newsroom import TopicNewsroom

__all__ = ["TraceLogger", "BaseNewsroom", "AgentExecutionError", "TopicNewsroom"]
````

### AFTER

````python
"""AIDEN 오케스트레이터 패키지."""
from .trace_logger import TraceLogger
from .base_newsroom import BaseNewsroom, AgentExecutionError
from .topic_newsroom import TopicNewsroom
from .content_newsroom import ContentNewsroom

__all__ = [
    "TraceLogger",
    "BaseNewsroom",
    "AgentExecutionError",
    "TopicNewsroom",
    "ContentNewsroom",
]
````

---

# 작업 4: tests/test_content_newsroom.py 신규

pytest 기반. 모의 callable로 토론 흐름 검증.

```python
"""
Content Newsroom 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable로 흐름 검증.
- iter 1에서 approved 즉시 종료
- iter 2에서 approved
- iter 3 강제 종료
- 에이전트 실패 시 강제 approved
- 입력 조립 규칙 (data_flow_spec §4-2)
"""
from __future__ import annotations

import json
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
            {"claim": "fact A", "status": "verified", "evidence": "...", "source_url": "...", "source_domain": "naver.com", "source_date": "2026-05"},
            {"claim": "fact B", "status": "verified", "evidence": "...", "source_url": "...", "source_domain": "naver.com", "source_date": "2026-05"},
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
    """DA가 pass_threshold=True 반환 (iter 1에서 종료 유도)"""
    iteration = _input["iteration"]
    count_map = {1: 5, 2: 3, 3: 1}
    n = count_map.get(iteration, 1)
    return {
        "iteration": iteration,
        "overall_verdict": "OK",
        "scores": {"originality": 8, "reader_value": 8, "tone_authenticity": 8, "structure": 8, "title_hook": 8},
        "critical_issues": [
            {"location": f"section {i}", "problem": f"문제 {i}", "suggestion": f"제안 {i}"}
            for i in range(n)
        ],
        "pass_threshold": True,
        "carried_over_from_previous": [] if iteration == 1 else [],
    }


def _da_fail(_input: dict) -> dict:
    """DA가 pass_threshold=False 반환 (재작성 유도)"""
    iteration = _input["iteration"]
    count_map = {1: 5, 2: 3, 3: 1}
    n = count_map.get(iteration, 1)
    return {
        "iteration": iteration,
        "overall_verdict": "Bad",
        "scores": {"originality": 4, "reader_value": 4, "tone_authenticity": 4, "structure": 4, "title_hook": 4},
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
    
    def test_iter1_approved_immediately(self, tracer, strategy):
        """iter 1에서 Editor approved → 즉시 종료"""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)
        
        assert result["decision"] == "approved"
        assert result["iteration"] == 1
        assert "final_content" in result
    
    def test_iter2_approved_after_revision(self, tracer, strategy):
        """iter 1 fail → iter 2 approved"""
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
    
    def test_iter3_force_approved_when_editor_says_needs_revision(self, tracer, strategy):
        """iter 3에서 Editor가 needs_revision 반환해도 오케스트레이터가 approved 강제"""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_fail, _editor_needs_revision)
        result = cn.run(category="맛집", strategy=strategy)
        
        assert result["decision"] == "approved"  # 강제됨
        assert result.get("_orchestrator_coerced_at_iter3") is True
        assert "known_weaknesses" in result["final_content"]
        assert len(result["final_content"]["known_weaknesses"]) > 0


class TestContentNewsroomAgentFailure:
    
    def test_writer_fails_iter1_force_approved(self, tracer, strategy):
        """Writer 실패 시 강제 approved (raise 안 함)"""
        def _writer_fail(_input):
            return {}  # sections 없음
        
        cn = ContentNewsroom(tracer, _writer_fail, _fc_ok, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)
        
        assert result["decision"] == "approved"
        assert result.get("_orchestrator_forced") is True
        assert "writer_failed" in result.get("_force_reason", "")
    
    def test_fc_raises_exception_force_approved(self, tracer, strategy):
        """Fact-Checker가 예외 던져도 raise 안 함"""
        def _fc_raise(_input):
            raise RuntimeError("FC down")
        
        cn = ContentNewsroom(tracer, _writer_ok, _fc_raise, _da_pass, _editor_approved)
        result = cn.run(category="맛집", strategy=strategy)
        
        assert result["decision"] == "approved"
        assert result.get("_orchestrator_forced") is True


class TestContentNewsroomInputAssembly:
    
    def test_writer_iter1_input_no_previous(self, tracer, strategy):
        """iter 1 Writer 입력에 previous_draft 등 없음"""
        captured = []
        
        def _writer_capturing(_input):
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
    
    def test_writer_iter2_input_has_previous(self, tracer, strategy):
        """iter 2 Writer 입력에 previous_draft, factcheck_log, critique, editor_instructions 모두 포함"""
        captured = []
        
        def _writer_capturing(_input):
            captured.append(dict(_input))
            return _writer_ok(_input)
        
        call_counter = {"editor": 0}
        
        def _editor_two_iters(_input):
            call_counter["editor"] += 1
            if call_counter["editor"] == 1:
                return _editor_needs_revision(_input)
            return _editor_approved(_input)
        
        cn = ContentNewsroom(tracer, _writer_capturing, _fc_ok, _da_pass, _editor_two_iters)
        cn.run(category="맛집", strategy=strategy)
        
        assert len(captured) >= 2
        second_call = captured[1]
        assert second_call["iteration"] == 2
        assert "previous_draft" in second_call
        assert "factcheck_log" in second_call
        assert "critique" in second_call
        assert "editor_instructions" in second_call
        # editor_instructions는 needs_revision의 revision_instructions를 그대로 받음
        assert isinstance(second_call["editor_instructions"], list)
    
    def test_da_iter2_input_has_previous_critiques(self, tracer, strategy):
        """iter 2 DA 입력에 previous_critiques + editor_response"""
        captured = []
        
        def _da_capturing(_input):
            captured.append(dict(_input))
            return _da_pass(_input)
        
        call_counter = {"editor": 0}
        
        def _editor_two_iters(_input):
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
    
    def test_trace_files_include_iteration_suffix(self, tracer, strategy):
        """iter 1에서 종료 시 04_writer_iter1.json 등 파일 생성"""
        cn = ContentNewsroom(tracer, _writer_ok, _fc_ok, _da_pass, _editor_approved)
        cn.run(category="맛집", strategy=strategy)
        
        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("04_writer_iter1" in f for f in files)
        assert any("05_fact_checker_iter1" in f for f in files)
        assert any("06_devils_advocate_iter1" in f for f in files)
        assert any("07_editor_iter1" in f for f in files)
    
    def test_trace_multi_iter(self, tracer, strategy):
        """iter 2 종료 시 iter1, iter2 파일 모두 생성"""
        call_counter = {"editor": 0}
        
        def _editor_two_iters(_input):
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
```

## 4-1. 테스트 실행 명령

```bash
cd C:\Users\jurong\Documents\claude_team\aiden
python -m pytest tests/test_content_newsroom.py -v
```

10개 테스트 모두 통과 확인. 전체 회귀:

```bash
python -m pytest tests/ -v
```

기존 16 + 신규 10 = 26 통과 확인.

---

# 작업 5: PROGRESS.md 업데이트

## 5-1. Phase 2 체크리스트 추가

```
- [x] content_newsroom.py: Stage 2 오케스트레이터 (iter 1/2/3 토론) _(2026-05-23)_
- [x] trace_logger.py: highlight 4종 추가 (Writer/FC/DA/Editor) _(2026-05-23)_
- [x] test_content_newsroom.py: 단위 테스트 10건 _(2026-05-23)_
```

## 5-2. 진행률 갱신

- 기존: 29/46 (63.0%)
- 신규: 32/46 (69.6%)

## 5-3. 의사결정 로그 추가

```
- 2026-05-23 묶음 2 Step 3-2 완료: Content Newsroom 오케스트레이터
  - 설계 결정 3건 확정:
    1. 종료 출력: Editor 전체 (final_content는 호출자가 추출)
    2. 에이전트 실패 시: 강제 approved (partial 결과 + trace에 fail 명시 + _orchestrator_forced 플래그)
    3. Fact-Checker 위치: 매 iter 재실행 (Editor confidence_score 트리거 정확도 우선)
  - 종료 조건 3가지: approved 즉시 / iter 3 + needs_revision 강제 종료 / 에이전트 실패 시 강제 종료
  - iter 2+ Writer/DA 입력 조립 (data_flow_spec §4-2 명세 그대로)
  - iter 3에서 Editor가 prompt 위반(needs_revision)해도 오케스트레이터가 한 번 더 보장 (_coerce_approved_at_iter3)
  - TraceLogger highlight 확장: Writer(draft v, 섹션 수), FC(confidence, verified 비율), DA(critique 수, 평균 점수, pass), Editor(decision, accepted/rejected)
  - 단위 테스트 10건 통과 (happy path 2, force termination 1, agent failure 2, input assembly 3, trace 2)
```

## 5-4. 마지막 업데이트 일자 2026-05-23 유지

---

# 실행 후 보고 항목

1. 신규 파일 2개 + 패치 2개 적용 확인
   - 신규: `backend/orchestrators/content_newsroom.py`, `tests/test_content_newsroom.py`
   - 패치: `backend/orchestrators/trace_logger.py` (_extract_highlight 확장), `backend/orchestrators/__init__.py` (export 추가)
2. 단위 테스트 실행 결과 (passed/failed 개수 + 전체 회귀 26건)
3. PROGRESS.md 진행률 29/46 → 32/46 (69.6%) 갱신 확인
4. 의사결정 로그 신규 항목 1건 확인
5. git status (스테이징 없음)
6. 다음 단계: 묶음 2 Step 3-3 (Game-ifier + 전체 통합) 진입 준비 완료

---

# 주의사항

- **코드 작성 + pytest 실행**.
- 기존 base_agent.py, topic_newsroom.py 등 손대지 말 것.
- 전체 회귀 실행 시 Step 3-1의 7건 + Step 2의 9건 모두 통과해야 함.
- 모든 파일 UTF-8 인코딩 명시. Python 3.11+ 타입 힌트.
- 실제 LLM 호출 없음. 모의 callable로 테스트.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

1. **content_newsroom.py 분량이 너무 큼**: 그대로 진행. 분할은 가독성·테스트 후 별도 리팩토링에서 검토.
2. **테스트 fixture 중복**: conftest.py 분리하지 말고 본 테스트 파일에 그대로 둠 (단순성 우선).
3. **_force_approve 또는 _coerce_approved_at_iter3 로직 의문**: 본 명세서 코드 그대로 사용. 변경 시 사용자 컨펌 필요.

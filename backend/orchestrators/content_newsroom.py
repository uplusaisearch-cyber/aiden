"""Content Newsroom (Stage 2).

흐름: 최대 3 iter 토론
  iter N: Writer → Fact-Checker → Devil's Advocate → Editor

종료 조건:
  - editor.decision == "approved" → 즉시 종료
  - iter == 3 AND decision == "needs_revision" → 강제 종료 (Editor가 known_weaknesses 포함)

데이터 흐름은 docs/architecture/data_flow_spec.md §4 참조.
"""
from __future__ import annotations

import difflib
import logging
from typing import Callable

from .base_newsroom import BaseNewsroom
from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3
DA_CRITICAL_COUNT_BY_ITER = {1: 5, 2: 3, 3: 1}  # 참고용 (prompt에 박혀있음)


class ContentNewsroom(BaseNewsroom):
    """Stage 2: Strategy Planner 의 final_topic 으로부터 final_content 도출.

    Usage:
        cn = ContentNewsroom(
            tracer=tracer,
            writer_fn=writer_callable,
            fact_checker_fn=fact_checker_callable,
            devils_advocate_fn=da_callable,
            editor_fn=editor_callable,
            base_order=4,  # Topic Newsroom 이 1-3 차지했으므로 4부터
        )
        result = cn.run(category="맛집", strategy=planner_output["final_topic"])
    """

    def __init__(
        self,
        tracer: TraceLogger,
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
        """Content Newsroom 실행.

        Args:
            category: 카테고리 (Writer 입력의 최상위 필드)
            strategy: Strategy Planner 의 final_topic 객체 그대로

        Returns:
            Editor 의 최종 출력 (``decision="approved"`` 보장).
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
                # B4-S2: Editor self-edit 정합성 검증. action="직접 수정함" 항목이 있는데
                # final_content 가 writer 원본과 거의 동일하면 known_weaknesses 에 경고 추가.
                self._verify_editor_self_edits(editor_output, writer_output)
                return editor_output

            if iteration == MAX_ITERATIONS:
                # iter 3에서 needs_revision이면 Editor 가 prompt 규칙대로 approved 로 강제 종료해야 하지만,
                # 만약 안 그랬다면 오케스트레이터가 한 번 더 보장.
                logger.warning(
                    "Editor returned needs_revision at iter 3. "
                    "Forcing approved with known_weaknesses."
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
        base: dict = {
            "iteration": iteration,
            "category": category,
            "strategy": strategy,
        }
        if iteration >= 2:
            base["previous_draft"] = previous_draft
            base["factcheck_log"] = factcheck_log
            base["critique"] = critique
            # editor.revision_instructions 를 Writer 가 그대로 사용
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
        base: dict = {
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
        """에이전트 실패 시 강제 approved (사용자 결정 #3).

        partial 결과로라도 final_content 구성. trace 에 fail 명시는 이미
        ``_execute_agent`` 에서 됨.
        """
        logger.warning(f"Force-approving due to failure: {fail_reason}")

        # annotated_draft 가 있으면 그걸, 없으면 writer_output 을 base 로
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

    def _verify_editor_self_edits(
        self,
        editor_output: dict,
        writer_output: dict,
    ) -> None:
        """Editor 가 ``accepted_critiques[].action == "직접 수정함"`` 으로 선언한
        항목이 있는데 ``final_content.sections`` 가 writer 원본과 거의 동일하면
        ``known_weaknesses`` 에 경고를 추가한다 (in-place).

        LLM self-policed 결함 보정. iter 3 가 아닌 정상 approved 분기에서도
        Editor 가 "수정함" 마킹은 하고 실제 수정 안 한 케이스를 외부에서 잡는다.
        """
        final_content = editor_output.get("final_content")
        if not isinstance(final_content, dict):
            return

        accepted = editor_output.get("accepted_critiques") or []
        direct_edits = [
            a for a in accepted
            if isinstance(a, dict) and "직접 수정" in str(a.get("action") or "")
        ]
        if not direct_edits:
            return

        def _sections_text(d: dict) -> str:
            sections = d.get("sections") or []
            parts: list[str] = []
            for s in sections:
                if isinstance(s, dict):
                    parts.append(str(s.get("body") or s.get("content") or ""))
            return "\n".join(parts)

        before = _sections_text(writer_output)
        after = _sections_text(final_content)
        if not before or not after:
            return

        ratio = difflib.SequenceMatcher(None, before, after).ratio()
        # 0.99 임계치 — 거의 byte-identical. 정상 편집이면 0.7~0.9 대로 떨어짐.
        if ratio >= 0.99:
            warn = (
                f"Editor 가 '직접 수정함' {len(direct_edits)}건을 선언했으나 "
                f"본문 변경 미검출 (sections 유사도 {ratio:.3f})"
            )
            known = list(final_content.get("known_weaknesses") or [])
            known.append(warn)
            final_content["known_weaknesses"] = known
            editor_output["_self_edit_verification"] = {
                "direct_edits_claimed": len(direct_edits),
                "sections_similarity": round(ratio, 3),
                "warning_added": True,
            }
            logger.warning("Editor self-edit 의심: %s", warn)

    def _coerce_approved_at_iter3(
        self,
        editor_output: dict,
        da_output: dict,
        factcheck_output: dict,
    ) -> dict:
        """iter 3에서 Editor 가 needs_revision 으로 끝낸 경우 prompt 규칙 위반.

        오케스트레이터가 한 번 더 보장: ``approved`` + ``known_weaknesses`` 채움.
        """
        coerced = dict(editor_output)
        coerced["decision"] = "approved"

        # final_content 가 없으면 최소 골격 구성
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

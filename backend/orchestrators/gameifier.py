"""Game-ifier (Stage 3).

흐름: Format Architect → HTML Builder
입력: ``Editor.final_content``
출력: 즉시 게시 가능한 HTML 문자열 + format_decision + html_meta
"""
from __future__ import annotations

import logging
from typing import Callable

from backend.core.base_agent import WhitelistedSubstitutor  # noqa: F401 (선택적 헬퍼)

from .base_newsroom import BaseNewsroom
from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class Gameifier(BaseNewsroom):
    """Stage 3: ``final_content`` → HTML.

    Usage:
        gi = Gameifier(
            tracer=tracer,
            format_architect_fn=fa_callable,
            html_builder_fn=hb_callable,
            base_order=8,  # Content Newsroom 이 4-7 차지했으므로 8부터
        )
        result = gi.run(final_content=editor_output["final_content"])
    """

    def __init__(
        self,
        tracer: TraceLogger,
        format_architect_fn: Callable[[dict], dict],
        html_builder_fn: Callable[[dict], dict],
        base_order: int = 8,
    ):
        super().__init__(tracer)
        self.format_architect_fn = format_architect_fn
        self.html_builder_fn = html_builder_fn
        self.base_order = base_order

    def run(self, final_content: dict) -> dict:
        """Game-ifier 실행.

        Args:
            final_content: Editor.final_content 객체.

        Returns:
            dict with:
                - html: 완성된 HTML 문자열
                - format_decision: Format Architect 출력
                - html_meta: HTML Builder 출력 메타
                - error: 실패 시 사유 (성공 시 없음)
        """
        # Step 1: Format Architect
        fa_input = final_content
        fa_output, fa_err = self._execute_agent(
            order=self.base_order,
            agent_name="format_architect",
            agent_callable=self.format_architect_fn,
            input_data=fa_input,
        )
        if fa_err or "selected_type" not in fa_output:
            logger.error(f"Format Architect failed: {fa_err}")
            return self._fallback_html(
                final_content=final_content,
                error=f"format_architect_failed: {fa_err}",
            )

        # Step 2: HTML Builder
        hb_input = {
            "final_content": final_content,
            "format_decision": fa_output,
        }
        hb_output, hb_err = self._execute_agent(
            order=self.base_order + 1,
            agent_name="html_builder",
            agent_callable=self.html_builder_fn,
            input_data=hb_input,
        )
        if hb_err or not hb_output.get("html"):
            logger.error(f"HTML Builder failed: {hb_err}")
            return self._fallback_html(
                final_content=final_content,
                error=f"html_builder_failed: {hb_err}",
                format_decision=fa_output,
            )

        return {
            "html": hb_output["html"],
            "format_decision": fa_output,
            "html_meta": {
                "selected_type_applied": hb_output.get("selected_type_applied"),
                "base_layout_used": hb_output.get("base_layout_used"),
                "interactive_template_used": hb_output.get("interactive_template_used"),
                "placeholder_substitutions": hb_output.get("placeholder_substitutions", []),
                "preserved_placeholders": hb_output.get("preserved_placeholders", []),
                "warnings": hb_output.get("warnings", []),
            },
        }

    @staticmethod
    def _fallback_html(
        final_content: dict,
        error: str,
        format_decision: dict | None = None,
    ) -> dict:
        """Format Architect 또는 HTML Builder 실패 시 최소 HTML 생성.

        ``Editor.final_content`` 를 plain HTML 로 변환.
        """
        title = final_content.get("title", "(제목 없음)")
        subtitle = final_content.get("subtitle", "")
        intro = final_content.get("intro", "")
        closing = final_content.get("closing", "")
        cta = final_content.get("cta", "")
        sections = final_content.get("sections", [])
        sources = final_content.get("sources", [])
        known_weaknesses = final_content.get("known_weaknesses", [])

        sections_html = "".join(
            f'<section class="plustab-section">'
            f'  <h2>{s.get("heading", "")}</h2>'
            f'  <div class="section-body">{s.get("body", "")}</div>'
            f'</section>'
            for s in sections
        )

        sources_html = ""
        if sources:
            items = "".join(
                f'<li><a href="{s.get("url", "#")}" target="_blank" title="새창열기">'
                f'{s.get("domain", "")} ({s.get("date", "")})</a></li>'
                for s in sources
            )
            sources_html = f'<aside class="sources"><h3>출처</h3><ul>{items}</ul></aside>'

        weaknesses_html = ""
        if known_weaknesses:
            items = "".join(f"<li>{w}</li>" for w in known_weaknesses)
            weaknesses_html = (
                f'<aside class="known-weaknesses">'
                f'<h3>알려진 약점 (투명성)</h3><ul>{items}</ul></aside>'
            )

        html = (
            f'<!-- Fallback HTML generated by Gameifier due to: {error} -->\n'
            f'<article class="plustab-article">\n'
            f'  <header><h1>{title}</h1>'
            f'<p class="subtitle">{subtitle}</p></header>\n'
            f'  <div class="intro">{intro}</div>\n'
            f'  {sections_html}\n'
            f'  <div class="closing">{closing}</div>\n'
            f'  <div class="cta">{cta}</div>\n'
            f'  {sources_html}\n'
            f'  {weaknesses_html}\n'
            f'</article>'
        )

        return {
            "html": html,
            "format_decision": format_decision or {"selected_type": "A", "_fallback": True},
            "html_meta": {
                "_orchestrator_fallback": True,
                "_fallback_reason": error,
                "warnings": [f"Gameifier fallback used: {error}"],
            },
            "error": error,
        }

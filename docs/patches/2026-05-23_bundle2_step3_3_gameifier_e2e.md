# 묶음 2 Step 3-3 작업 명세서 — Game-ifier + 전체 파이프라인 통합

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2의 Step 3-3 (최종)  
**범위**: Game-ifier 오케스트레이터 + 전체 파이프라인 CLI + 9개 에이전트 실제 LLM E2E + HTML 산출물  
**실행 방식**: 코드 작성 + pytest 단위 테스트 + 실제 LLM 호출 9회 + 브라우저 검증

---

## Step 3 분할 진행 상태

| Step | 작업 | 상태 |
|---|---|---|
| Step 3-1 | data_flow_spec + 트레이스 + Topic Newsroom | ✅ |
| Step 3-2 | Content Newsroom (iter 1/2/3) | ✅ |
| Step 2.5 (재시도) | 조기 LLM 통합 (Topic + Content 실측 검증) | ✅ |
| **Step 3-3 (이번)** | Game-ifier + 전체 파이프라인 통합 + 9 에이전트 E2E | ✅ |

---

## 본 명세서 작업 개요

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `backend/orchestrators/gameifier.py` | 신규 |
| 2 | `backend/orchestrators/__init__.py` | 패치 (Gameifier export) |
| 3 | `backend/orchestrators/trace_logger.py` | 패치 (highlight 2종 추가) |
| 4 | `backend/orchestrators/full_pipeline.py` | 신규 (3 Newsroom 통합) |
| 5 | `backend/agents/concrete_agents.py` | 패치 (Format Architect + HTML Builder callable 추가) |
| 6 | `backend/utils/whitelisted_substitutor_helper.py` | 신규 (선택, 헬퍼) |
| 7 | `scripts/run_full_pipeline.py` | 신규 (E2E CLI 스크립트) |
| 8 | `tests/test_gameifier.py` | 신규 (단위 테스트) |
| 9 | `tests/test_full_pipeline.py` | 신규 (모의 LLM 통합 테스트) |
| 10 | 9 에이전트 실제 LLM E2E 실행 | 실행 + 브라우저 검증 |
| 11 | `docs/early_integration_report.md` | E2E 결과 append |
| 12 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 |
| 13 | `docs/architecture/data_flow_spec.md` | Stage 3 보강 |

---

## 설계 결정사항 (사용자 확정)

| # | 결정 | 영향 |
|---|---|---|
| 1 | 통합 범위: **CLI만** | FastAPI / Next.js UI는 묶음 3로 |
| 2 | 실제 LLM E2E: **전체 9 에이전트 실행** | 발표용 메타 산출물 1호 확보 |
| 3 | HTML 검증: **브라우저 확인** | `runs/<run_id>/final_output.html` 저장 + 사용자 수동 확인 |

---

# 작업 1: backend/orchestrators/gameifier.py 신규

Stage 3 오케스트레이터. Format Architect → HTML Builder 단방향.

```python
"""
Game-ifier (Stage 3).

흐름: Format Architect → HTML Builder
입력: Editor.final_content
출력: 즉시 게시 가능한 HTML 문자열 + format_decision + html_meta
"""
from __future__ import annotations

import logging
from typing import Callable

from backend.core.base_agent import WhitelistedSubstitutor

from .base_newsroom import BaseNewsroom

logger = logging.getLogger(__name__)


class Gameifier(BaseNewsroom):
    """
    Stage 3: final_content → HTML.
    
    Usage:
        gi = Gameifier(
            tracer=tracer,
            format_architect_fn=fa_callable,
            html_builder_fn=hb_callable,
            base_order=8,  # Content Newsroom이 4-7 차지했으므로 8부터
        )
        result = gi.run(final_content=editor_output["final_content"])
    """
    
    def __init__(
        self,
        tracer,
        format_architect_fn: Callable[[dict], dict],
        html_builder_fn: Callable[[dict], dict],
        base_order: int = 8,
    ):
        super().__init__(tracer)
        self.format_architect_fn = format_architect_fn
        self.html_builder_fn = html_builder_fn
        self.base_order = base_order
    
    def run(self, final_content: dict) -> dict:
        """
        Game-ifier 실행.
        
        Args:
            final_content: Editor.final_content 객체
        
        Returns:
            dict with:
                - html: 완성된 HTML 문자열
                - format_decision: Format Architect 출력
                - html_meta: HTML Builder 출력 메타
                - error: 실패 시 사유
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
        """
        Format Architect 또는 HTML Builder 실패 시 최소 HTML 생성.
        Editor.final_content를 plain HTML로 변환.
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
```

---

# 작업 2: backend/orchestrators/__init__.py 패치

### BEFORE

```python
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
```

### AFTER

```python
"""AIDEN 오케스트레이터 패키지."""
from .trace_logger import TraceLogger
from .base_newsroom import BaseNewsroom, AgentExecutionError
from .topic_newsroom import TopicNewsroom
from .content_newsroom import ContentNewsroom
from .gameifier import Gameifier
from .full_pipeline import FullPipeline

__all__ = [
    "TraceLogger",
    "BaseNewsroom",
    "AgentExecutionError",
    "TopicNewsroom",
    "ContentNewsroom",
    "Gameifier",
    "FullPipeline",
]
```

---

# 작업 3: backend/orchestrators/trace_logger.py 패치

`_extract_highlight`에 Format Architect / HTML Builder 추가.

### BEFORE (메서드 끝부분)

```python
        if agent_name == "editor":
            decision = output_data.get("decision", "?")
            accepted = len(output_data.get("accepted_critiques", []))
            rejected = len(output_data.get("rejected_critiques", []))
            return f"decision={decision}, accepted={accepted}, rejected={rejected}"
        # 기타 에이전트는 Step 3-3에서 추가
        return ""
```

### AFTER

```python
        if agent_name == "editor":
            decision = output_data.get("decision", "?")
            accepted = len(output_data.get("accepted_critiques", []))
            rejected = len(output_data.get("rejected_critiques", []))
            return f"decision={decision}, accepted={accepted}, rejected={rejected}"
        if agent_name == "format_architect":
            stype = output_data.get("selected_type", "?")
            base = output_data.get("base_layout", "-")
            interactive = output_data.get("interactive", {}).get("template", "none")
            return f"type={stype}, base={base}, interactive={interactive}"
        if agent_name == "html_builder":
            stype = output_data.get("selected_type_applied", "?")
            subs = len(output_data.get("placeholder_substitutions", []))
            preserved = len(output_data.get("preserved_placeholders", []))
            warns = len(output_data.get("warnings", []))
            return f"type={stype}, subs={subs}, preserved={preserved}, warnings={warns}"
        return ""
```

---

# 작업 4: backend/orchestrators/full_pipeline.py 신규

3 Newsroom 통합 진입점.

```python
"""
AIDEN 전체 파이프라인 통합.

Topic Newsroom → Content Newsroom → Game-ifier
하나의 TraceLogger를 공유하여 9개 에이전트 trace가 동일 run_id에 누적됨.
"""
from __future__ import annotations

import logging
from typing import Callable

from .content_newsroom import ContentNewsroom
from .gameifier import Gameifier
from .topic_newsroom import TopicNewsroom
from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class FullPipeline:
    """
    AIDEN 전체 파이프라인.
    
    Usage:
        pipeline = FullPipeline(
            tracer=tracer,
            agents=agent_dict,  # 9개 에이전트 callable
        )
        result = pipeline.run(category="맛집")
    """
    
    def __init__(
        self,
        tracer: TraceLogger,
        agents: dict[str, Callable[[dict], dict]],
    ):
        """
        Args:
            tracer: TraceLogger 인스턴스 (모든 에이전트 공유)
            agents: 키는 다음 9개 - 
                scout, analyst, planner,
                writer, fact_checker, devils_advocate, editor,
                format_architect, html_builder
        """
        self.tracer = tracer
        self.agents = agents
        self._validate_agents()
    
    def _validate_agents(self):
        required = {
            "scout", "analyst", "planner",
            "writer", "fact_checker", "devils_advocate", "editor",
            "format_architect", "html_builder",
        }
        missing = required - set(self.agents.keys())
        if missing:
            raise ValueError(f"FullPipeline 누락 에이전트: {missing}")
    
    def run(self, category: str, target_date: str | None = None) -> dict:
        """
        전체 파이프라인 실행.
        
        Returns:
            dict with:
                - stage_1: Topic Newsroom 결과
                - stage_2: Content Newsroom 결과
                - stage_3: Game-ifier 결과
                - final_html: 최종 HTML 문자열
                - status: completed | partial | failed
        """
        result = {
            "stage_1": None,
            "stage_2": None,
            "stage_3": None,
            "final_html": None,
            "status": "started",
        }
        
        # Stage 1: Topic Newsroom
        logger.info("Stage 1: Topic Newsroom")
        tn = TopicNewsroom(
            tracer=self.tracer,
            scout_fn=self.agents["scout"],
            analyst_fn=self.agents["analyst"],
            planner_fn=self.agents["planner"],
        )
        stage_1 = tn.run(category=category, target_date=target_date)
        result["stage_1"] = stage_1
        
        if "final_topic" not in stage_1:
            logger.error("Stage 1 실패: final_topic 없음")
            result["status"] = "failed_stage_1"
            return result
        
        # Stage 2: Content Newsroom
        logger.info("Stage 2: Content Newsroom")
        cn = ContentNewsroom(
            tracer=self.tracer,
            writer_fn=self.agents["writer"],
            fact_checker_fn=self.agents["fact_checker"],
            devils_advocate_fn=self.agents["devils_advocate"],
            editor_fn=self.agents["editor"],
            base_order=4,
        )
        stage_2 = cn.run(category=category, strategy=stage_1["final_topic"])
        result["stage_2"] = stage_2
        
        if "final_content" not in stage_2:
            logger.error("Stage 2 실패: final_content 없음")
            result["status"] = "failed_stage_2"
            return result
        
        # Stage 3: Game-ifier
        logger.info("Stage 3: Game-ifier")
        gi = Gameifier(
            tracer=self.tracer,
            format_architect_fn=self.agents["format_architect"],
            html_builder_fn=self.agents["html_builder"],
            base_order=8,
        )
        stage_3 = gi.run(final_content=stage_2["final_content"])
        result["stage_3"] = stage_3
        result["final_html"] = stage_3.get("html")
        
        if stage_3.get("error"):
            result["status"] = "partial"  # Stage 3 fallback 사용된 케이스
        else:
            result["status"] = "completed"
        
        return result
```

---

# 작업 5: backend/agents/concrete_agents.py 패치

Format Architect + HTML Builder callable 추가.

기존 파일에 다음 함수 추가:

```python
def build_gameifier_agents(llm_client) -> dict[str, Callable[[dict], dict]]:
    """Game-ifier용 2개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "format_architect": make_agent_callable(
            "08_format_architect.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
        "html_builder": make_agent_callable(
            "09_html_builder.md", llm_client, use_grounding=False, prompt_loader=loader
        ),
    }


def build_all_agents(llm_client) -> dict[str, Callable[[dict], dict]]:
    """9개 에이전트 전체 callable 생성. FullPipeline 입력용."""
    loader = PromptLoader()
    
    topic = {
        "scout": make_agent_callable("01_trend_scout.md", llm_client, use_grounding=True, prompt_loader=loader),
        "analyst": make_agent_callable("02_audience_analyst.md", llm_client, use_grounding=False, prompt_loader=loader),
        "planner": make_agent_callable("03_strategy_planner.md", llm_client, use_grounding=False, prompt_loader=loader),
    }
    content = {
        "writer": make_agent_callable("04_writer.md", llm_client, use_grounding=False, prompt_loader=loader),
        "fact_checker": make_agent_callable("05_fact_checker.md", llm_client, use_grounding=True, prompt_loader=loader),
        "devils_advocate": make_agent_callable("06_devils_advocate.md", llm_client, use_grounding=False, prompt_loader=loader),
        "editor": make_agent_callable("07_editor_in_chief.md", llm_client, use_grounding=False, prompt_loader=loader),
    }
    game = {
        "format_architect": make_agent_callable("08_format_architect.md", llm_client, use_grounding=False, prompt_loader=loader),
        "html_builder": make_agent_callable("09_html_builder.md", llm_client, use_grounding=False, prompt_loader=loader),
    }
    return {**topic, **content, **game}
```

---

# 작업 6: scripts/run_full_pipeline.py 신규

E2E CLI 스크립트. 9개 에이전트 한 번에 실행 + HTML 파일 저장.

```python
"""
AIDEN 전체 파이프라인 실행 스크립트 (E2E).

사용법:
    python scripts/run_full_pipeline.py --category 맛집

실행 후 runs/<timestamp>_<run_id>/ 폴더에:
- agents/01~09_*.json (9개 trace)
- summary.jsonl
- metadata.json
- final_output.html  ← 브라우저로 열어 확인
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from backend.agents.concrete_agents import build_all_agents
from backend.llm.gemini_client import GeminiClient
from backend.orchestrators.full_pipeline import FullPipeline
from backend.orchestrators.trace_logger import TraceLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("full_pipeline")


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="콘텐츠 카테고리")
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()
    
    # Gemini 클라이언트
    client = GeminiClient(model=args.model)
    
    # 9개 에이전트 callable
    agents = build_all_agents(client)
    
    # Tracer (3 Stage 공유)
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"E2E run started: {tracer.run_dir}")
    
    # Full Pipeline 실행
    pipeline = FullPipeline(tracer=tracer, agents=agents)
    
    try:
        result = pipeline.run(category=args.category)
    except Exception as e:
        logger.exception("FullPipeline 실행 중 예외")
        result = {"status": "exception", "error": str(e)}
    
    # final_output.html 저장
    final_html = result.get("final_html")
    if final_html:
        html_path = tracer.run_dir / "final_output.html"
        # 스탠드얼론 HTML 래퍼 (브라우저 직접 열기용)
        wrapped = (
            "<!DOCTYPE html>\n"
            '<html lang="ko"><head><meta charset="utf-8">'
            f"<title>{args.category} - AIDEN 산출물</title>"
            "<style>"
            "body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;"
            "max-width:680px;margin:0 auto;padding:20px;line-height:1.7;color:#222;}"
            "h1{font-size:24px;}h2{font-size:18px;margin-top:32px;}"
            ".sources{margin-top:32px;padding:16px;background:#f7f7f7;border-radius:8px;}"
            ".known-weaknesses{margin-top:16px;padding:16px;background:#fff4f4;"
            "border-left:4px solid #c00;}"
            "</style></head><body>\n"
            f"{final_html}\n"
            "</body></html>"
        )
        html_path.write_text(wrapped, encoding="utf-8")
        logger.info(f"Final HTML saved: {html_path}")
    
    # metadata 작성
    tracer.write_metadata(
        user_input={"category": args.category, "model": args.model},
        status=result.get("status", "unknown"),
        notes="Step 3-3 E2E 9 에이전트 완주 실험",
    )
    
    # 요약 로그
    logger.info(f"=== E2E Run Summary ===")
    logger.info(f"Run dir: {tracer.run_dir}")
    logger.info(f"Status: {result.get('status')}")
    
    stage_1 = result.get("stage_1") or {}
    stage_2 = result.get("stage_2") or {}
    stage_3 = result.get("stage_3") or {}
    
    if "final_topic" in stage_1:
        logger.info(f"Stage 1 title: {stage_1['final_topic'].get('title')}")
    if "final_content" in stage_2:
        logger.info(f"Stage 2 iteration: {stage_2.get('iteration')}")
        logger.info(f"Stage 2 forced: {stage_2.get('_orchestrator_forced', False)}")
    if stage_3.get("format_decision"):
        logger.info(f"Stage 3 type: {stage_3['format_decision'].get('selected_type')}")
    
    if final_html:
        logger.info(f"HTML output: {tracer.run_dir / 'final_output.html'}")
        logger.info("브라우저에서 위 파일을 열어 검증하세요.")


if __name__ == "__main__":
    main()
```

---

# 작업 7: tests/test_gameifier.py 신규

```python
"""
Game-ifier 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable로 흐름 검증.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.orchestrators.gameifier import Gameifier
from backend.orchestrators.trace_logger import TraceLogger


@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


@pytest.fixture
def final_content() -> dict:
    return {
        "category": "맛집",
        "title": "테스트 제목",
        "subtitle": "테스트 부제",
        "intro": "도입",
        "sections": [
            {"heading": "s1", "body": "본문 1 [출처: naver.com, 2026-05]"},
            {"heading": "s2", "body": "본문 2"},
        ],
        "closing": "마무리",
        "cta": "CTA",
        "sources": [{"domain": "naver.com", "url": "https://...", "date": "2026-05"}],
        "known_weaknesses": [],
    }


def _fa_a_type(_input: dict) -> dict:
    return {
        "format_analysis": "단순 정보 콘텐츠",
        "selected_type": "A",
        "base_layout": "A",
        "type_reasoning": "정보 전달 위주, 인터랙티브 가치 없음",
        "layout_hints": {
            "hero_image_needed": True,
            "image_count": 2,
            "image_descriptions": ["히어로 이미지", "섹션 이미지"],
        },
        "placeholder_locations": [
            {"name": "HERO_IMAGE_URL", "location": "section.hero", "render_zone": "outside_comment"}
        ],
    }


def _hb_ok(_input: dict) -> dict:
    return {
        "html": "<article><h1>테스트 제목</h1><section>...</section></article>",
        "selected_type_applied": "A",
        "base_layout_used": "A",
        "interactive_template_used": None,
        "placeholder_substitutions": [],
        "preserved_placeholders": ["{{HERO_IMAGE_URL}}"],
        "warnings": [],
    }


class TestGameifierHappyPath:
    
    def test_a_type_no_interactive(self, tracer, final_content):
        gi = Gameifier(tracer, _fa_a_type, _hb_ok)
        result = gi.run(final_content=final_content)
        
        assert "html" in result
        assert result["format_decision"]["selected_type"] == "A"
        assert "html_meta" in result
    
    def test_trace_files_created(self, tracer, final_content):
        gi = Gameifier(tracer, _fa_a_type, _hb_ok)
        gi.run(final_content=final_content)
        
        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("08_format_architect" in f for f in files)
        assert any("09_html_builder" in f for f in files)


class TestGameifierFallback:
    
    def test_fa_fail_uses_fallback(self, tracer, final_content):
        def _fa_fail(_input):
            return {}  # selected_type 없음
        
        gi = Gameifier(tracer, _fa_fail, _hb_ok)
        result = gi.run(final_content=final_content)
        
        assert "html" in result
        assert result["error"].startswith("format_architect_failed")
        assert result["html_meta"]["_orchestrator_fallback"] is True
        # fallback HTML에 타이틀이 들어가야 함
        assert "테스트 제목" in result["html"]
    
    def test_hb_fail_uses_fallback(self, tracer, final_content):
        def _hb_fail(_input):
            return {"html": ""}  # html 비어있음
        
        gi = Gameifier(tracer, _fa_a_type, _hb_fail)
        result = gi.run(final_content=final_content)
        
        assert "html" in result
        assert result["error"].startswith("html_builder_failed")
        assert "테스트 제목" in result["html"]
    
    def test_fa_raises_exception_fallback(self, tracer, final_content):
        def _fa_raise(_input):
            raise RuntimeError("FA down")
        
        gi = Gameifier(tracer, _fa_raise, _hb_ok)
        result = gi.run(final_content=final_content)
        
        assert result["html_meta"]["_orchestrator_fallback"] is True


class TestGameifierBaseOrder:
    
    def test_custom_base_order(self, tracer, final_content):
        """base_order=8이 아닌 다른 값 사용 시 파일명 변경"""
        gi = Gameifier(tracer, _fa_a_type, _hb_ok, base_order=10)
        gi.run(final_content=final_content)
        
        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        assert any("10_format_architect" in f for f in files)
        assert any("11_html_builder" in f for f in files)
```

---

# 작업 8: tests/test_full_pipeline.py 신규

모의 callable로 전체 파이프라인 흐름 검증.

```python
"""
FullPipeline 통합 테스트.

실제 LLM 호출 없이 모의 9 에이전트 callable로 전체 흐름 검증.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.orchestrators.full_pipeline import FullPipeline
from backend.orchestrators.trace_logger import TraceLogger


@pytest.fixture
def tracer(tmp_path: Path) -> TraceLogger:
    return TraceLogger.new_run(base_dir=str(tmp_path / "runs"))


def _scout(_input):
    return {
        "category": _input["category"],
        "search_queries_used": ["q"],
        "trending_topics": [
            {"topic": f"T{i}", "why_trending": "wt", "sources": [{"domain": "n.com", "url": "u", "date": "2026-05"}], "estimated_volume": "medium", "longevity": "evergreen"}
            for i in range(3)
        ],
        "summary": "s",
    }


def _analyst(_input):
    return {
        "category": _input["category"],
        "audience_evaluation": [
            {"topic": t["topic"], "fit_score": 8, "reasoning": "r", "concerns": "", "angle_suggestion": "a"}
            for t in _input["trending_topics"]
        ],
        "verdict": {"top_choice_topic": _input["trending_topics"][0]["topic"], "reasoning": "r"},
    }


def _planner(_input):
    top = _input["audience_analyst"]["verdict"]["top_choice_topic"]
    return {
        "category": _input["category"],
        "deliberation": "d",
        "final_topic": {
            "category": _input["category"],
            "title": top, "angle": "a", "target_persona": "p",
            "content_type_recommendation": "A", "type_reasoning": "tr",
            "estimated_read_time_min": 3,
            "key_messages": ["m1", "m2", "m3"],
            "data_grounding": [{"fact": "f", "source": {"domain": "n.com", "url": "u", "date": "2026-05"}}],
        },
        "rejected_topics": [{"topic": "T1", "reason": "r"}, {"topic": "T2", "reason": "r"}],
    }


def _writer(_input):
    return {
        "draft_version": _input["iteration"],
        "category": _input["category"],
        "title": "WT", "subtitle": "WS", "intro": "WI",
        "sections": [
            {"heading": "h1", "body": "b1", "fact_claims": ["f1"]},
            {"heading": "h2", "body": "b2", "fact_claims": ["f2"]},
        ],
        "closing": "WC", "cta": "CT",
        "revision_notes": [] if _input["iteration"] == 1 else [{"target": "h1", "applied": "fixed"}],
    }


def _fc(_writer):
    return {
        "verification_log": [
            {"claim": c, "status": "verified", "evidence": "e", "source_url": "u", "source_domain": "n.com", "source_date": "2026-05"}
            for s in _writer["sections"] for c in s["fact_claims"]
        ],
        "annotated_draft": {
            "title": _writer["title"], "subtitle": _writer["subtitle"], "intro": _writer["intro"],
            "sections": [
                {"heading": s["heading"], "body": s["body"] + " [출처: n.com, 2026-05]",
                 "fact_claims": [{"claim": c, "status": "verified"} for c in s["fact_claims"]]}
                for s in _writer["sections"]
            ],
            "closing": _writer["closing"], "cta": _writer["cta"],
        },
        "confidence_score": 10,
        "summary": "all verified",
    }


def _da_pass(_input):
    iteration = _input["iteration"]
    return {
        "iteration": iteration,
        "overall_verdict": "ok",
        "scores": {"originality": 8, "reader_value": 8, "tone_authenticity": 8, "structure": 8, "title_hook": 8},
        "critical_issues": [
            {"location": f"s{i}", "problem": "p", "suggestion": "s"}
            for i in range({1: 5, 2: 3, 3: 1}.get(iteration, 1))
        ],
        "pass_threshold": True,
        "carried_over_from_previous": [],
    }


def _editor_approved(_input):
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


def _format_architect(_input):
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


def _html_builder(_input):
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
    
    def test_e2e_happy_path(self, tracer, agents):
        pipeline = FullPipeline(tracer=tracer, agents=agents)
        result = pipeline.run(category="맛집")
        
        assert result["status"] == "completed"
        assert "final_html" in result
        assert result["final_html"]  # not empty
        assert result["stage_1"]["final_topic"]["category"] == "맛집"
        assert result["stage_2"]["decision"] == "approved"
        assert result["stage_3"]["format_decision"]["selected_type"] == "A"
    
    def test_all_9_agents_traced(self, tracer, agents):
        pipeline = FullPipeline(tracer=tracer, agents=agents)
        pipeline.run(category="맛집")
        
        agents_dir = tracer.run_dir / "agents"
        files = sorted(p.name for p in agents_dir.iterdir())
        
        # 01 ~ 09 모두 있어야 함 (iter 1만 종료된 경우)
        for prefix in ["01_trend_scout", "02_audience_analyst", "03_strategy_planner",
                       "04_writer_iter1", "05_fact_checker_iter1",
                       "06_devils_advocate_iter1", "07_editor_iter1",
                       "08_format_architect", "09_html_builder"]:
            assert any(prefix in f for f in files), f"Missing trace file: {prefix}"
    
    def test_missing_agent_raises(self, tracer):
        incomplete = {"scout": _scout, "analyst": _analyst}  # 나머지 누락
        
        with pytest.raises(ValueError, match="누락"):
            FullPipeline(tracer=tracer, agents=incomplete)
    
    def test_stage_1_failure_short_circuits(self, tracer, agents):
        def _scout_fail(_input):
            return {}
        
        bad_agents = {**agents, "scout": _scout_fail}
        pipeline = FullPipeline(tracer=tracer, agents=bad_agents)
        result = pipeline.run(category="맛집")
        
        assert result["status"] == "failed_stage_1"
        assert result["stage_2"] is None
        assert result["stage_3"] is None
```

## 8-1. 테스트 실행

```bash
cd C:\Users\jurong\Documents\claude_team\aiden
python -m pytest tests/ -v
```

전체 회귀 = 기존 26 + 신규 (gameifier 7 + full_pipeline 4) = 37 통과 확인.

---

# 작업 9: 실제 LLM E2E 실행 (9 에이전트 완주)

테스트 통과 후 실제 실행.

```bash
python scripts/run_full_pipeline.py --category 맛집
```

⚠️ **비용 추정**: Topic 3 + Content 4-12 + Game-ifier 2 = 9-17 호출 ≈ $0.005-0.02 (수십원)

## 9-1. 실행 후 확인 체크리스트

- [ ] `runs/<run_id>/agents/` 에 9개 파일 모두 생성됨 (01~09, iter는 1-3 중 종료 시점)
- [ ] `runs/<run_id>/summary.jsonl` 에 동일 수 라인
- [ ] `runs/<run_id>/metadata.json` 의 status == "completed"
- [ ] `runs/<run_id>/final_output.html` 파일 존재 + size > 1KB
- [ ] **브라우저로 final_output.html 열기 → 사용자(나) 수동 확인**

## 9-2. 브라우저 검증 사항

사용자가 final_output.html 열어서:
- [ ] 한국어 제목·본문 정상 표시
- [ ] 섹션 구조 깔끔
- [ ] `[출처: ...]` 마커 본문 inline에 노출됨
- [ ] CSS 깨짐 없음 (래퍼 스타일 적용 확인)
- [ ] CTA 영역 표시
- [ ] (선택) C 타입이면 인터랙티브 컴포넌트 동작 (JS 콘솔 에러 없음)

---

# 작업 10: docs/early_integration_report.md E2E 결과 append

기존 보고서 끝에 다음 섹션 추가:

```markdown
---

## Step 3-3 E2E 9 에이전트 완주 (2026-05-23)

### 실행 결과
- run_id: <채워넣기>
- 카테고리: 맛집
- 상태: <completed | partial | failed>
- 9 에이전트 통과: 
  - 01 Trend Scout <✅/❌>
  - 02 Audience Analyst <✅/❌>
  - 03 Strategy Planner <✅/❌>
  - 04 Writer (iter <N>) <✅/❌>
  - 05 Fact-Checker <✅/❌>
  - 06 Devil's Advocate <✅/❌>
  - 07 Editor (final iter <N>, decision <approved>) <✅/❌>
  - 08 Format Architect <✅/❌>
  - 09 HTML Builder <✅/❌>
- 최종 산출물: runs/<run_id>/final_output.html
- 총 호출 횟수 / 추정 비용

### 브라우저 검증 결과
- HTML 렌더링: <정상/이슈>
- 한국어 표시: <정상/이슈>
- 출처 마커 inline: <정상/이슈>
- 인터랙티브 컴포넌트 (해당 시): <정상/이슈>

### 발견 이슈
(이슈 형식대로 기록, 없으면 "이슈 없음" 명시)

### Step 3-3 진입 후 회고
- 9 에이전트 첫 완주 의미: <한 줄>
- 묶음 3 진입 가능 여부: <가능/조건부 가능/추가 작업 필요>
- 발표용 메타 산출물 1호 확보 여부
```

---

# 작업 11: docs/architecture/data_flow_spec.md §6 보강

기존 §6 (Stage 3: Game-ifier)을 다음 내용으로 교체:

```markdown
## 6. Stage 3: Game-ifier

### 6-1. Format Architect
- **입력**: `editor_output["final_content"]`
- **출력**: prompt에 명시된 스키마 (selected_type, base_layout, interactive, layout_hints, placeholder_locations)

### 6-2. HTML Builder
- **입력 조립**:
  ```python
  html_builder_input = {
      "final_content": editor_output["final_content"],
      "format_decision": format_architect_output
  }
  ```
- **출력**: html(문자열) + meta(placeholder_substitutions, preserved_placeholders, warnings)

### 6-3. Gameifier 오케스트레이터
- 두 에이전트 단방향. iter 없음.
- 에이전트 실패 시 fallback: Editor.final_content를 plain HTML로 변환 (`_orchestrator_fallback` 플래그)
- fallback HTML도 `known_weaknesses` 섹션 포함 (투명성)

### 6-4. FullPipeline 통합
- 3 Newsroom을 단일 TraceLogger로 묶어 실행
- base_order 자동 분배: Topic 1-3, Content 4-7 (iter별 suffix), Game-ifier 8-9
- 최종 HTML은 `runs/<run_id>/final_output.html`로 저장 (스크립트가 처리, 오케스트레이터는 dict만 반환)
```

---

# 작업 12: PROGRESS.md 업데이트

## 12-1. Phase 2 체크리스트 추가

```
- [x] Gameifier 오케스트레이터 (Stage 3) _(2026-05-23)_
- [x] FullPipeline 통합 (3 Newsroom) _(2026-05-23)_
- [x] run_full_pipeline.py E2E 스크립트 + HTML 래퍼 _(2026-05-23)_
- [x] test_gameifier.py 단위 테스트 _(2026-05-23)_
- [x] test_full_pipeline.py 통합 테스트 _(2026-05-23)_
- [x] 9 에이전트 실제 LLM E2E 완주 + 브라우저 검증 _(2026-05-23)_
- [x] data_flow_spec.md §6 Stage 3 보강 _(2026-05-23)_
```

## 12-2. 진행률 갱신

- 기존: 36/46 (78.3%)
- 신규: 43/46 (93.5%)

## 12-3. 의사결정 로그 추가

```
- 2026-05-23 묶음 2 Step 3-3 완료: Game-ifier + 전체 파이프라인 통합 + 9 에이전트 E2E 완주
  - 설계 결정 3건 확정:
    1. 통합 범위: CLI만 (FastAPI/UI는 묶음 3로)
    2. 실제 LLM E2E: 전체 9 에이전트 실행 (발표용 메타 산출물 1호 확보)
    3. HTML 검증: 브라우저 확인 (final_output.html 스탠드얼론 래퍼)
  - Gameifier: Format Architect → HTML Builder, 실패 시 fallback HTML 자동 생성
  - FullPipeline: 단일 TraceLogger로 3 Newsroom 통합, base_order 자동 분배 (1-3 / 4-7 / 8-9)
  - 실제 9 에이전트 E2E 1회 완주 성공 (run_id: <채워넣기>)
  - 단위 테스트 11건 추가 통과 (전체 회귀 37건)
  - 묶음 2 거의 완료. 잔여: P2 이슈 R3 (FC iter3 verification_log) 처리 + 잠재 추가 검증
```

---

# 실행 후 보고 항목

1. 신규 파일 생성 확인 (line count)
   - `backend/orchestrators/gameifier.py`
   - `backend/orchestrators/full_pipeline.py`
   - `scripts/run_full_pipeline.py`
   - `tests/test_gameifier.py`
   - `tests/test_full_pipeline.py`
2. 패치 적용 확인
   - `backend/orchestrators/__init__.py` (Gameifier, FullPipeline export)
   - `backend/orchestrators/trace_logger.py` (Format Architect, HTML Builder highlight)
   - `backend/agents/concrete_agents.py` (build_gameifier_agents, build_all_agents)
   - `docs/architecture/data_flow_spec.md` (§6 보강)
3. 단위 테스트 결과 (전체 회귀 37건 통과 여부)
4. **실제 LLM E2E 실행 결과**:
   - run_id
   - 상태 (completed / partial / failed)
   - 9 에이전트 각각 통과 여부
   - 총 호출 횟수 + 추정 비용
   - final_output.html 생성 여부 + 파일 크기
5. PROGRESS.md 진행률 36/46 → 43/46 (93.5%) 갱신 확인
6. early_integration_report.md E2E 섹션 append 확인
7. git status (스테이징 없음)
8. **사용자(나) 검증 안내**:
   - `runs/<run_id>/final_output.html` 절대 경로 출력
   - "브라우저에서 위 파일을 열어 확인하세요" 메시지

---

# 주의사항

- **실제 LLM 호출 비용 발생**. 한 번 완주 기준 수십원 수준.
- E2E 실행 실패 시 trace 파일에 모든 정보 남으므로 raw 결과 그대로 보고.
- 모의 callable 테스트와 실제 LLM 결과가 다를 수 있음 (특히 한국어 출력 톤·JSON 강건성).
- final_output.html은 스탠드얼론 (외부 CSS/JS 의존 X) — 브라우저로 바로 열 수 있어야 함.
- runs/ 폴더는 .gitignore로 제외됨 (Step 2.5 직후 처리됨).
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

1. **Format Architect가 selected_type을 "A|B|C" 외 값 반환**: trace에 기록 + Gameifier가 fallback HTML 사용.
2. **HTML Builder가 잘못된 HTML 반환** (예: `<article>` 누락): Step 2.5 P2처럼 P1으로 기록. 묶음 3에서 prompt 보강.
3. **CALCULATOR formula에 eval-like 표현 발견**: 즉시 P0. mathjs 외 표현 제거하도록 prompt 패치 필요 (별도 작업).
4. **9 에이전트 중 1개라도 실패**: 어느 에이전트인지 명시. fallback 동작했는지 trace로 확인. 사용자에게 결정 위임 (재시도 / Step 3-3 부분 완료로 진행).
5. **final_output.html 한국어 깨짐**: charset 메타 태그 확인. UTF-8로 작성됐는지 검증.

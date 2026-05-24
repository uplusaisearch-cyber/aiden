# 묶음 2 Step 3-1 작업 명세서 — Topic Newsroom 오케스트레이터

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2의 Step 3-1  
**범위**: data_flow_spec.md + 트레이스 로깅 + Topic Newsroom 오케스트레이터 + 단위 테스트  
**실행 방식**: 코드 작성 + pytest 단위 테스트 실행

---

## Step 3 분할 계획

| Step | 작업 | 본 명세서 범위 |
|---|---|---|
| **Step 3-1 (이번)** | data_flow_spec.md + 트레이스 로깅 + Topic Newsroom (Scout → Analyst → Planner, 단방향) | ✅ |
| Step 3-2 | Content Newsroom (iter 1/2/3, Writer ↔ Fact-Checker ↔ DA ↔ Editor) | 다음 |
| Step 3-3 | Game-ifier (Format Architect → HTML Builder) + 전체 파이프라인 통합 | 다음다음 |

각 Step 끝나고 검증 후 다음 진입.

---

## 본 명세서 작업 개요

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `docs/architecture/data_flow_spec.md` | 신규 |
| 2 | `backend/orchestrators/trace_logger.py` | 신규 (트레이스 로깅 기반) |
| 3 | `backend/orchestrators/base_newsroom.py` | 신규 (자체 mini-state-machine 베이스) |
| 4 | `backend/orchestrators/topic_newsroom.py` | 신규 |
| 5 | `tests/test_topic_newsroom.py` | 신규 (단위 테스트, 모의 LLM) |
| 6 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 |
| 7 | `docs/NEXT_BUNDLE_NOTES.md` | §7-2, §7-3 상태 변경 |

---

## 설계 결정사항 (사용자 확정)

| # | 결정 | 영향 |
|---|---|---|
| 1 | 이미지 URL: **placeholder 그대로** | HTML Builder 단계에서 default URL 사용. 이미지 생성 에이전트 없음. |
| 2 | 오케스트레이터: **자체 mini-state-machine 클래스** | base_newsroom.py에 베이스 클래스, 각 Newsroom 상속 |
| 3 | 트레이스 로그: **단계별 JSON + 한 줄 요약 jsonl** | runs/{timestamp}/ 구조 |
| 4 | Step 3 분할 진행 | 3-1/3-2/3-3 |

---

# 작업 1: docs/architecture/data_flow_spec.md 신규

AIDEN 전체 데이터 흐름 명세서. 발표·핸드오프 시 핵심 참조 문서.

폴더 `docs/architecture/`가 없으면 신규 생성.

```markdown
# AIDEN 데이터 흐름 명세서 (Data Flow Spec)

**버전**: 1.0  
**작성일**: 2026-05-23  
**목적**: 9개 에이전트 간 입출력 매핑 + 오케스트레이터의 데이터 변환 규칙 명시

---

## 1. 전체 파이프라인 개요

```
[User Input: category]
        │
        ▼
┌──────────────────────────────┐
│  Stage 1: Topic Newsroom     │  단방향, 1회 실행
│  Scout → Analyst → Planner   │
└──────────────────────────────┘
        │ final_topic
        ▼
┌──────────────────────────────┐
│  Stage 2: Content Newsroom   │  max 3 iter 토론
│  Writer ↔ FC ↔ DA ↔ Editor   │
└──────────────────────────────┘
        │ final_content
        ▼
┌──────────────────────────────┐
│  Stage 3: Game-ifier         │  단방향
│  Format Architect → HTML B   │
└──────────────────────────────┘
        │ html
        ▼
[Output: Plustab-ready HTML]
```

## 2. Stage 1: Topic Newsroom

### 2-1. Trend Scout
- **입력**: 오케스트레이터가 직접 조립
  ```json
  {
    "category": "<user input>",
    "target_date": "<오늘 날짜 ISO>"
  }
  ```
- **출력**: prompt에 명시된 스키마 그대로

### 2-2. Audience Analyst
- **입력 조립 규칙**:
  ```python
  audience_input = {
      "category": scout_output["category"],
      "trending_topics": scout_output["trending_topics"]  # 이것만 전달
  }
  # summary, search_queries_used는 무시
  ```

### 2-3. Strategy Planner
- **입력 조립 규칙**:
  ```python
  planner_input = {
      "category": scout_output["category"],
      "trend_scout": scout_output,         # 전체 전달
      "audience_analyst": analyst_output   # 전체 전달
  }
  ```
- **출력의 `final_topic`이 Stage 2의 시작점**

## 3. Stage 1 → Stage 2 핸드오프

```python
# Topic Newsroom 출력 (planner_output) → Content Newsroom 입력
writer_input_iter1 = {
    "iteration": 1,
    "category": planner_output["final_topic"]["category"],
    "strategy": planner_output["final_topic"]  # final_topic 전체를 strategy로 매핑
}
```

**중요**: Writer의 입력 키 `strategy`는 `final_topic` 객체와 동치. category는 한 단계 위로 끌어올림.

## 4. Stage 2: Content Newsroom (Step 3-2에서 상세)

### 4-1. Round-Robin 흐름 (iter 1)
```
Writer → Fact-Checker → Devil's Advocate → Editor
```

### 4-2. iter 2+ 입력 조립
Writer.input v2+:
```python
writer_input_iter2 = {
    "iteration": 2,
    "category": <상동>,
    "strategy": <상동>,
    "previous_draft": writer_output_v1,
    "factcheck_log": factchecker_output_v1,
    "critique": da_output_v1,
    "editor_instructions": editor_output_v1["revision_instructions"]
}
```

Devil's Advocate.input v2+:
```python
da_input_iter2 = {
    "iteration": 2,
    "category": <상동>,
    "annotated_draft": factchecker_output_v2,
    "previous_critiques": da_output_v1["critical_issues"],
    "editor_response": {
        "accepted_critiques": editor_output_v1["accepted_critiques"],
        "rejected_critiques": editor_output_v1["rejected_critiques"]
    }
}
```

### 4-3. 종료 조건
- `editor_output["decision"] == "approved"` → 즉시 종료
- `iteration == 3` AND `editor_output["decision"] == "needs_revision"` → 강제 종료 (Editor가 approved + known_weaknesses 명시)

## 5. Stage 2 → Stage 3 핸드오프

```python
# Editor 최종 출력 → Format Architect 입력
format_architect_input = editor_output["final_content"]
```

## 6. Stage 3: Game-ifier (Step 3-3에서 상세)

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
- **출력의 `html`이 최종 산출물**

## 7. 트레이스 로그 구조

실행마다 다음 폴더 구조 생성:

```
runs/
  2026-05-23T14-30-00_{run_id}/
    metadata.json              # 입력 + 전체 진행 요약
    summary.jsonl              # 에이전트별 한 줄 요약 (시각화용)
    agents/
      01_trend_scout.json
      02_audience_analyst.json
      03_strategy_planner.json
      04_writer_iter1.json
      05_fact_checker_iter1.json
      06_devils_advocate_iter1.json
      07_editor_iter1.json
      (iter 2/3 있으면 그대로 누적)
      08_format_architect.json
      09_html_builder.json
    final_output.html           # 최종 HTML
```

## 8. 에러 처리 원칙

- 각 에이전트가 잘못된 JSON 반환 → 1회 재시도, 실패 시 trace에 기록 후 fallback
- LLM API 호출 실패 → 지수 백오프 3회 재시도
- 오케스트레이터는 절대 raise 안 함. 실패 시 trace에 명시 후 최선 결과 반환.

## 9. 변경 이력

| 일자 | 변경 |
|---|---|
| 2026-05-23 | 초안 작성 (Step 3-1) |
```

---

# 작업 2: backend/orchestrators/trace_logger.py 신규

폴더 `backend/orchestrators/`가 없으면 생성하고 `__init__.py`도 추가.

```python
"""
AIDEN 트레이스 로거.

각 에이전트 실행 결과를 runs/{run_id}/agents/*.json 으로 저장.
한 줄 요약은 runs/{run_id}/summary.jsonl 로 append.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class TraceLogger:
    """
    실행당 1개 인스턴스. 모든 에이전트 결과를 단일 run 폴더에 저장.
    
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
        self.started_at = datetime.utcnow()
        self._step_count = 0
    
    @classmethod
    def new_run(cls, base_dir: str = "runs") -> "TraceLogger":
        """새 run 폴더 생성 후 TraceLogger 반환."""
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
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
        """
        에이전트 1회 실행 기록.
        
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
        
        record = {
            "order": order,
            "agent_name": agent_name,
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat(),
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
        ended_at = datetime.utcnow()
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
```

---

# 작업 3: backend/orchestrators/base_newsroom.py 신규

mini-state-machine 베이스 클래스. 각 Newsroom이 상속.

```python
"""
AIDEN 오케스트레이터 베이스.

각 Newsroom(Stage 1/2/3)은 BaseNewsroom 상속.
미니 state-machine: 단계 정의 + 실행 + 트레이스 기록.
"""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from .trace_logger import TraceLogger

logger = logging.getLogger(__name__)


class AgentExecutionError(Exception):
    """에이전트 실행 중 발생한 오류 (오케스트레이터는 raise 안 함, 내부에서 처리)."""
    pass


class BaseNewsroom(ABC):
    """
    Newsroom 베이스 클래스.
    
    하위 클래스는 다음을 구현:
    - _stages: 단계 정의 리스트
    - run: 메인 실행 메서드
    """
    
    def __init__(self, tracer: TraceLogger):
        self.tracer = tracer
    
    @abstractmethod
    def run(self, *args, **kwargs) -> dict:
        """메인 실행 메서드. 하위 클래스에서 구현."""
        ...
    
    def _execute_agent(
        self,
        order: int,
        agent_name: str,
        agent_callable,
        input_data: dict,
        iteration: int | None = None,
        max_retries: int = 1,
    ) -> tuple[dict, str | None]:
        """
        단일 에이전트 실행 + 트레이스 기록.
        
        Args:
            order: 실행 순서
            agent_name: snake_case
            agent_callable: callable(input_data: dict) -> dict
            input_data: 입력
            iteration: Content Newsroom의 iter (없으면 None)
            max_retries: JSON 파싱 실패 시 재시도 횟수 (default 1)
        
        Returns:
            (output_data, error_message or None)
        """
        start = time.time()
        error = None
        output_data: dict = {}
        
        for attempt in range(max_retries + 1):
            try:
                output_data = agent_callable(input_data)
                if not isinstance(output_data, dict):
                    raise AgentExecutionError(
                        f"Agent {agent_name} did not return dict: got {type(output_data).__name__}"
                    )
                error = None
                break
            except Exception as e:
                error = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"Agent {agent_name} attempt {attempt + 1} failed: {error}"
                )
                if attempt < max_retries:
                    time.sleep(0.5)  # short backoff
        
        duration_ms = int((time.time() - start) * 1000)
        
        self.tracer.log_agent_step(
            order=order,
            agent_name=agent_name,
            iteration=iteration,
            input_data=input_data,
            output_data=output_data,
            duration_ms=duration_ms,
            error=error,
        )
        
        return output_data, error
```

---

# 작업 4: backend/orchestrators/topic_newsroom.py 신규

Topic Newsroom 오케스트레이터. Stage 1.

```python
"""
Topic Newsroom (Stage 1).

흐름: Trend Scout → Audience Analyst → Strategy Planner
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Callable

from .base_newsroom import BaseNewsroom

logger = logging.getLogger(__name__)


class TopicNewsroom(BaseNewsroom):
    """
    Stage 1: 사용자가 입력한 category로부터 final_topic 도출.
    
    Usage:
        tn = TopicNewsroom(
            tracer=tracer,
            scout_fn=scout_callable,
            analyst_fn=analyst_callable,
            planner_fn=planner_callable,
        )
        result = tn.run(category="맛집")
    """
    
    def __init__(
        self,
        tracer,
        scout_fn: Callable[[dict], dict],
        analyst_fn: Callable[[dict], dict],
        planner_fn: Callable[[dict], dict],
    ):
        super().__init__(tracer)
        self.scout_fn = scout_fn
        self.analyst_fn = analyst_fn
        self.planner_fn = planner_fn
    
    def run(self, category: str, target_date: str | None = None) -> dict:
        """
        Topic Newsroom 실행.
        
        Args:
            category: 사용자 입력 카테고리
            target_date: 트렌드 검색 기준일 (ISO 형식). None이면 오늘.
        
        Returns:
            Strategy Planner 출력 (final_topic 포함). 실패 시 partial dict.
        """
        if target_date is None:
            target_date = date.today().isoformat()
        
        # Step 1: Trend Scout
        scout_input = {
            "category": category,
            "target_date": target_date,
        }
        scout_output, scout_err = self._execute_agent(
            order=1,
            agent_name="trend_scout",
            agent_callable=self.scout_fn,
            input_data=scout_input,
        )
        if scout_err or not scout_output.get("trending_topics"):
            logger.error(f"Trend Scout failed or returned empty: {scout_err}")
            return {"error": "trend_scout_failed", "partial": scout_output}
        
        # Step 2: Audience Analyst
        analyst_input = {
            "category": scout_output.get("category", category),
            "trending_topics": scout_output["trending_topics"],
            # summary, search_queries_used는 의도적으로 제외 (data_flow_spec §2-2)
        }
        analyst_output, analyst_err = self._execute_agent(
            order=2,
            agent_name="audience_analyst",
            agent_callable=self.analyst_fn,
            input_data=analyst_input,
        )
        if analyst_err or not analyst_output.get("audience_evaluation"):
            logger.error(f"Audience Analyst failed: {analyst_err}")
            return {"error": "audience_analyst_failed", "partial": analyst_output}
        
        # Step 3: Strategy Planner
        planner_input = {
            "category": scout_output.get("category", category),
            "trend_scout": scout_output,
            "audience_analyst": analyst_output,
        }
        planner_output, planner_err = self._execute_agent(
            order=3,
            agent_name="strategy_planner",
            agent_callable=self.planner_fn,
            input_data=planner_input,
        )
        if planner_err or not planner_output.get("final_topic"):
            logger.error(f"Strategy Planner failed: {planner_err}")
            return {"error": "strategy_planner_failed", "partial": planner_output}
        
        return planner_output
```

---

# 작업 5: tests/test_topic_newsroom.py 신규

pytest 기반. **실제 LLM 호출 없음.** 모의 callable 사용.

```python
"""
Topic Newsroom 오케스트레이터 단위 테스트.

실제 LLM 호출 없이 모의 callable로 흐름 검증.
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
    """tmp_path에 run 폴더 생성."""
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
                {"fact": "test fact", "source": {"domain": "naver.com", "url": "https://...", "date": "2026-05"}}
            ],
        },
        "rejected_topics": [
            {"topic": "토픽 1", "reason": "test"},
            {"topic": "토픽 2", "reason": "test"},
        ],
    }


# ---- Tests ------------------------------------------------------------------

class TestTopicNewsroom:
    
    def test_happy_path(self, tracer):
        """3개 에이전트 모두 정상 → final_topic 반환"""
        tn = TopicNewsroom(tracer, _scout_ok, _analyst_ok, _planner_ok)
        result = tn.run(category="맛집")
        
        assert "final_topic" in result
        assert result["final_topic"]["category"] == "맛집"
        assert "title" in result["final_topic"]
    
    def test_trace_files_created(self, tracer, tmp_path):
        """트레이스 파일 3개 + summary.jsonl + metadata가 생성됨"""
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
    
    def test_analyst_input_excludes_summary(self, tracer):
        """data_flow_spec §2-2: analyst 입력에 summary, search_queries_used 없어야 함"""
        captured_input = {}
        
        def _analyst_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _analyst_ok(_input)
        
        tn = TopicNewsroom(tracer, _scout_ok, _analyst_capturing, _planner_ok)
        tn.run(category="맛집")
        
        assert "category" in captured_input
        assert "trending_topics" in captured_input
        assert "summary" not in captured_input
        assert "search_queries_used" not in captured_input
    
    def test_planner_receives_both_outputs(self, tracer):
        """data_flow_spec §2-3: planner 입력에 trend_scout + audience_analyst 전체"""
        captured_input = {}
        
        def _planner_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _planner_ok(_input)
        
        tn = TopicNewsroom(tracer, _scout_ok, _analyst_ok, _planner_capturing)
        tn.run(category="맛집")
        
        assert "trend_scout" in captured_input
        assert "audience_analyst" in captured_input
        assert "trending_topics" in captured_input["trend_scout"]
        assert "audience_evaluation" in captured_input["audience_analyst"]
    
    def test_scout_failure_returns_error(self, tracer):
        """Trend Scout 실패 시 error 반환 (raise 안 함)"""
        def _scout_fail(_input: dict) -> dict:
            return {}  # trending_topics 없음
        
        tn = TopicNewsroom(tracer, _scout_fail, _analyst_ok, _planner_ok)
        result = tn.run(category="맛집")
        
        assert result.get("error") == "trend_scout_failed"
    
    def test_target_date_defaults_to_today(self, tracer):
        """target_date 미전달 시 오늘 날짜 사용"""
        captured_input = {}
        
        def _scout_capturing(_input: dict) -> dict:
            captured_input.update(_input)
            return _scout_ok(_input)
        
        tn = TopicNewsroom(tracer, _scout_capturing, _analyst_ok, _planner_ok)
        tn.run(category="맛집")
        
        assert "target_date" in captured_input
        # ISO format YYYY-MM-DD
        assert len(captured_input["target_date"]) == 10
        assert captured_input["target_date"][4] == "-"
    
    def test_agent_exception_recorded_in_trace(self, tracer):
        """에이전트가 예외 던져도 오케스트레이터는 raise 안 함, trace에 기록"""
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
```

## 5-1. 테스트 실행 명령

```bash
cd C:\Users\jurong\Documents\claude_team\aiden
python -m pytest tests/test_topic_newsroom.py -v
```

7개 테스트 모두 통과 확인.

---

# 작업 6: backend/orchestrators/__init__.py 신규

빈 파일이거나 아래 내용:

```python
"""AIDEN 오케스트레이터 패키지."""
from .trace_logger import TraceLogger
from .base_newsroom import BaseNewsroom, AgentExecutionError
from .topic_newsroom import TopicNewsroom

__all__ = ["TraceLogger", "BaseNewsroom", "AgentExecutionError", "TopicNewsroom"]
```

---

# 작업 7: PROGRESS.md 업데이트

## 7-1. Phase 2 체크리스트 추가 (✅ 처리)

```
- [x] data_flow_spec.md 작성 (Stage 1~3 흐름 명세) _(2026-05-23)_
- [x] trace_logger.py: 단계별 JSON + summary.jsonl _(2026-05-23)_
- [x] base_newsroom.py: 미니 state-machine 베이스 _(2026-05-23)_
- [x] topic_newsroom.py: Stage 1 오케스트레이터 _(2026-05-23)_
- [x] test_topic_newsroom.py: 단위 테스트 7건 _(2026-05-23)_
```

## 7-2. 진행률 갱신

- 기존: 24/46 (52.2%)
- 신규: 29/46 (63.0%)

## 7-3. 의사결정 로그 추가

```
- 2026-05-23 묶음 2 Step 3-1 완료: Topic Newsroom 오케스트레이터 + 트레이스 로깅 기반 구축
  - 설계 결정 4건 확정:
    1. 이미지 URL: placeholder 그대로 (별도 생성 에이전트 없음, MVP)
    2. 오케스트레이터: 자체 mini-state-machine 클래스 (BaseNewsroom 상속 구조)
    3. 트레이스 로그: 단계별 JSON + summary.jsonl + metadata.json
    4. Step 3 분할: 3-1/3-2/3-3
  - data_flow_spec.md 신규: 9 에이전트 입출력 매핑 + 오케스트레이터 변환 규칙
  - TraceLogger: runs/{timestamp}_{run_id}/ 구조, agent별 highlight 추출
  - BaseNewsroom: _execute_agent로 트레이스 + 재시도 + 에러 처리 캡슐화
  - TopicNewsroom: Stage 1 단방향 흐름, summary/search_queries_used 의도적 제외 명시
  - 단위 테스트 7건 통과 (happy path, trace 생성, 입력 매핑, 에러 처리)
```

## 7-4. NEXT_BUNDLE_NOTES.md §7-2, §7-3 상태 변경

### §7-2 끝에 추가:
```
> **상태 (2026-05-23)**: MVP 결정 - placeholder URL 그대로 유지. 별도 이미지 생성 에이전트는 묶음 3 또는 v2에서 검토. HTML Builder가 default URL 패턴 사용.
```

### §7-3 끝에 추가:
```
> **상태 (2026-05-23)**: data_flow_spec.md 신규 작성으로 해소. Stage 1~3 전체 핸드오프 규칙 명세화. Step 3-2/3-3 진행하면서 보강 예정.
```

---

# 실행 후 보고 항목

1. 신규 파일 5개 생성 확인 (line count + 핵심 클래스명)
   - `docs/architecture/data_flow_spec.md`
   - `backend/orchestrators/__init__.py`
   - `backend/orchestrators/trace_logger.py`
   - `backend/orchestrators/base_newsroom.py`
   - `backend/orchestrators/topic_newsroom.py`
   - `tests/test_topic_newsroom.py`
2. 단위 테스트 실행 결과 (passed/failed 개수)
3. PROGRESS.md 진행률 24/46 → 29/46 (63.0%) 갱신 확인
4. NEXT_BUNDLE_NOTES.md §7-2, §7-3 상태 라인 추가 확인
5. git status (스테이징 없음)
6. 다음 단계: 묶음 2 Step 3-2 (Content Newsroom, iter 1/2/3 토론) 진입 준비 완료

---

# 주의사항

- **코드 작성 + pytest 실행**.
- 기존 폴더 구조(backend/core/base_agent.py 등) 보존. `backend/orchestrators/`는 신규 폴더.
- pathlib.Path 사용. 백슬래시 직접 사용 금지 (Windows 환경).
- 모든 파일 UTF-8 인코딩 명시.
- 타입 힌트 필수 (Python 3.11+ 문법).
- 트레이스 로거의 `_extract_highlight`는 이번 단계에선 3개 에이전트만 처리. 나머지는 Step 3-2/3-3에서 추가.
- 실제 LLM 호출 없음. 테스트는 모의 callable 사용.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

1. **`backend/orchestrators/` 폴더 부재**: 신규 생성.
2. **기존 `tests/__init__.py` 없음**: 빈 파일 생성.
3. **pytest 실행 시 import 에러**: `backend/__init__.py`, `backend/orchestrators/__init__.py` 등 모든 경로 패키지화 확인. 필요 시 추가.
4. **pytest 미설치**: `pip install pytest --break-system-packages` 로 설치.
5. **`runs/` 폴더 git 추적 문제**: 본 작업에선 무시. 추후 .gitignore에 추가 권장 (이번 작업 아님).

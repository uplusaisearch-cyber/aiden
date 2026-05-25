# 묶음 2 Step 2.5 작업 명세서 — 조기 LLM 통합 (Early Integration)

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2 Step 2.5 (계획 외 끼워넣기, 위험 조기 발견용)  
**범위**: Gemini API 클라이언트 + 최소 통합 코드 + 실제 LLM 1회 실행 + 발견 이슈 정리  
**실행 방식**: 코드 작성 + 실제 LLM 호출 + 결과 보고

---

## 목적 (왜 이 단계가 끼워들어가는가)

지금까지 9개 prompt + 베이스 + 오케스트레이터 2개는 **모두 모의 callable로만 검증**. 실제 Gemini는 한 번도 안 돌려봄.

**Step 3-3 진입 전에 한 번 실제로 돌려봐야 하는 이유**:
1. LLM이 한국어 JSON 출력에서 한글 키를 박을 수 있음 → 파싱 깨짐
2. Google Search Grounding 결과가 prompt 예상과 다를 수 있음
3. `[출처: domain, YYYY-MM]` 마커 안 박을 수 있음
4. iter 1에서 Editor가 `decision` enum 다른 값 출력 가능
5. **이런 이슈를 Step 3-3 만들고 발견하면 prompt 다시 다 손봐야 함**

→ 지금 발견하는 게 싸다.

---

## 본 명세서 작업 개요

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `backend/llm/__init__.py` | 신규 |
| 2 | `backend/llm/gemini_client.py` | 신규 |
| 3 | `backend/agents/concrete_agents.py` | 신규 |
| 4 | `scripts/run_topic_newsroom_live.py` | 신규 (실제 실행 스크립트) |
| 5 | `scripts/run_content_newsroom_live.py` | 신규 (실제 실행 스크립트) |
| 6 | `.env.example` | 신규 (API 키 가이드) |
| 7 | `docs/early_integration_report.md` | **실행 후** 사용자가 작성 (Claude Code가 초안) |
| 8 | `PROGRESS.md` | 체크리스트 + 의사결정 로그 |

**중요**: 본 작업은 실제 LLM 호출 비용 발생. 그러나 Topic 3회 + Content 4회 ≈ 총 7회 호출이라 매우 저렴.

---

## 설계 결정사항

| # | 결정 | 비고 |
|---|---|---|
| 1 | LLM 제공자: **Google AI Studio (Gemini)** | 메모리 기준, 1차 선택 |
| 2 | 모델: **Gemini 2.0 Flash** (역할별 차등은 v2에서) | Step 2.5는 통합 검증이 목표. 모델 분기는 미루기. |
| 3 | Grounding: **Trend Scout + Fact-Checker만 사용** | prompt 명세대로 |
| 4 | 환경 변수: `GOOGLE_AI_STUDIO_API_KEY` | `.env` 로드 (python-dotenv) |
| 5 | Content Newsroom 실행 범위: **iter 1만** | 비용 절감 + 1회 검증에 충분. iter 2+ 흐름은 모의 테스트로 이미 검증됨. |
| 6 | 출력 파싱 실패 시: **JSON 추출 1회 재시도 후 raw 보존** | base_newsroom의 max_retries=1 활용 |

---

# 작업 1: backend/llm/__init__.py 신규

폴더 신규. 빈 파일 또는:

```python
"""AIDEN LLM 통합 패키지."""
from .gemini_client import GeminiClient

__all__ = ["GeminiClient"]
```

---

# 작업 2: backend/llm/gemini_client.py 신규

Gemini API wrapper. system_prompt + user_input → JSON dict 반환.

```python
"""
Gemini API 클라이언트.

목적: system_prompt + user_input(dict) → JSON dict 반환.
Grounding 옵션 지원 (Trend Scout / Fact-Checker용).

의존: google-generativeai
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError:
    genai = None
    logger.warning("google-generativeai 미설치. pip install google-generativeai")


class GeminiClient:
    """
    Gemini API wrapper.
    
    Usage:
        client = GeminiClient(api_key="...", model="gemini-2.0-flash")
        result_dict = client.call(
            system_prompt="...",
            user_input={"category": "맛집"},
            use_grounding=True,
        )
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash",
    ):
        if genai is None:
            raise RuntimeError("google-generativeai package not installed")
        
        self.api_key = api_key or os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_AI_STUDIO_API_KEY 미설정. .env 또는 환경 변수에 설정 필요."
            )
        
        genai.configure(api_key=self.api_key)
        self.model_name = model
    
    def call(
        self,
        system_prompt: str,
        user_input: dict,
        use_grounding: bool = False,
        temperature: float = 0.7,
    ) -> dict:
        """
        Gemini 호출 후 JSON dict 반환.
        
        Args:
            system_prompt: 에이전트 system prompt (PromptLoader로 로드된)
            user_input: 에이전트 입력 dict
            use_grounding: Google Search Grounding 사용 여부
            temperature: 생성 temperature
        
        Returns:
            파싱된 JSON dict
        
        Raises:
            ValueError: JSON 파싱 실패 시 (재시도 1회 후에도 실패)
        """
        tools = None
        if use_grounding:
            # Gemini 2.0 Flash는 Google Search를 tool로 사용
            tools = "google_search_retrieval"
        
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            tools=tools,
        )
        
        # user_input을 JSON 문자열로 직렬화해 전달
        user_message = (
            "다음 JSON 입력을 받아 system prompt의 출력 형식에 정확히 맞는 JSON만 반환해주세요. "
            "코드블록 마크업(```json)은 포함해도 좋고, JSON 외 다른 텍스트는 절대 포함하지 마세요.\n\n"
            f"입력:\n```json\n{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```"
        )
        
        generation_config = genai.types.GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" if not use_grounding else None,
            # grounding 사용 시 response_mime_type 강제 못함 (제약)
        )
        
        try:
            response = model.generate_content(
                user_message,
                generation_config=generation_config,
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
        
        raw_text = response.text or ""
        return self._parse_json(raw_text)
    
    @staticmethod
    def _parse_json(text: str) -> dict:
        """
        Gemini 응답에서 JSON 추출. 
        ```json ... ``` 코드블록 또는 raw JSON 처리.
        """
        text = text.strip()
        
        # 코드블록 제거
        m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
        if m:
            text = m.group(1).strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # JSON 추출 한 번 더 시도: 첫 { 와 마지막 } 사이
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
            
            logger.error(f"JSON parse failed. Raw text head: {text[:300]}")
            raise ValueError(f"Failed to parse Gemini response as JSON: {e}")
```

---

# 작업 3: backend/agents/concrete_agents.py 신규

9개 에이전트를 callable로 wrap. base_agent의 PromptLoader + GeminiClient 결합.

```python
"""
구체 에이전트 callable 모음.

각 에이전트는 base_newsroom._execute_agent에 callable로 전달됨.
agent_callable(input_data: dict) -> dict 시그니처.
"""
from __future__ import annotations

import logging
from typing import Callable

from backend.core.base_agent import PromptLoader
from backend.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


def make_agent_callable(
    prompt_filename: str,
    llm_client: GeminiClient,
    use_grounding: bool = False,
    prompt_loader: PromptLoader | None = None,
) -> Callable[[dict], dict]:
    """
    prompt 파일과 LLM 클라이언트로부터 에이전트 callable 생성.
    
    Args:
        prompt_filename: 예 "04_writer.md"
        llm_client: GeminiClient 인스턴스
        use_grounding: Google Search Grounding 사용 여부
        prompt_loader: 재사용 시 인스턴스 주입 (None이면 새로 생성)
    
    Returns:
        agent_callable(input_data: dict) -> dict
    """
    loader = prompt_loader or PromptLoader()
    system_prompt = loader.load(prompt_filename)
    
    def _call(input_data: dict) -> dict:
        return llm_client.call(
            system_prompt=system_prompt,
            user_input=input_data,
            use_grounding=use_grounding,
        )
    
    _call.__name__ = f"agent_{prompt_filename.replace('.md', '')}"
    return _call


def build_topic_newsroom_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """Topic Newsroom용 3개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "scout": make_agent_callable("01_trend_scout.md", llm_client, use_grounding=True, prompt_loader=loader),
        "analyst": make_agent_callable("02_audience_analyst.md", llm_client, use_grounding=False, prompt_loader=loader),
        "planner": make_agent_callable("03_strategy_planner.md", llm_client, use_grounding=False, prompt_loader=loader),
    }


def build_content_newsroom_agents(llm_client: GeminiClient) -> dict[str, Callable[[dict], dict]]:
    """Content Newsroom용 4개 에이전트 callable 생성."""
    loader = PromptLoader()
    return {
        "writer": make_agent_callable("04_writer.md", llm_client, use_grounding=False, prompt_loader=loader),
        "fact_checker": make_agent_callable("05_fact_checker.md", llm_client, use_grounding=True, prompt_loader=loader),
        "devils_advocate": make_agent_callable("06_devils_advocate.md", llm_client, use_grounding=False, prompt_loader=loader),
        "editor": make_agent_callable("07_editor_in_chief.md", llm_client, use_grounding=False, prompt_loader=loader),
    }
```

---

# 작업 4: scripts/run_topic_newsroom_live.py 신규

폴더 `scripts/` 가 없으면 생성. 실제 LLM 실행 스크립트.

```python
"""
Topic Newsroom 실제 LLM 실행 스크립트.

사용법:
    python scripts/run_topic_newsroom_live.py --category 맛집

실행 후 runs/{timestamp}_{run_id}/ 폴더에 trace 생성됨.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from backend.agents.concrete_agents import build_topic_newsroom_agents
from backend.llm.gemini_client import GeminiClient
from backend.orchestrators.topic_newsroom import TopicNewsroom
from backend.orchestrators.trace_logger import TraceLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("topic_newsroom_live")


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, help="콘텐츠 카테고리")
    parser.add_argument("--model", default="gemini-2.0-flash")
    args = parser.parse_args()
    
    # Gemini 클라이언트
    client = GeminiClient(model=args.model)
    
    # 에이전트 callable
    agents = build_topic_newsroom_agents(client)
    
    # Tracer
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"Run started: {tracer.run_dir}")
    
    # Topic Newsroom 실행
    tn = TopicNewsroom(
        tracer=tracer,
        scout_fn=agents["scout"],
        analyst_fn=agents["analyst"],
        planner_fn=agents["planner"],
    )
    
    try:
        result = tn.run(category=args.category)
        status = "completed" if "final_topic" in result else "partial"
    except Exception as e:
        logger.exception("Topic Newsroom 실행 중 예외 발생")
        result = {"error": str(e)}
        status = "failed"
    
    tracer.write_metadata(
        user_input={"category": args.category, "model": args.model},
        status=status,
        notes="Step 2.5 조기 LLM 통합 실험",
    )
    
    logger.info(f"Run finished: {tracer.run_dir}")
    logger.info(f"Status: {status}")
    if "final_topic" in result:
        logger.info(f"Final title: {result['final_topic'].get('title')}")
    

if __name__ == "__main__":
    main()
```

---

# 작업 5: scripts/run_content_newsroom_live.py 신규

```python
"""
Content Newsroom 실제 LLM 실행 스크립트 (iter 1만).

사용법: Topic Newsroom 결과의 final_topic JSON을 stdin 또는 파일로 받음
    python scripts/run_content_newsroom_live.py --topic-file runs/<run_id>/agents/03_strategy_planner.json

실행 후 runs/{timestamp}_{run_id}/ 폴더에 trace 생성됨.
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

from backend.agents.concrete_agents import build_content_newsroom_agents
from backend.llm.gemini_client import GeminiClient
from backend.orchestrators.content_newsroom import ContentNewsroom
from backend.orchestrators.trace_logger import TraceLogger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s: %(message)s",
)
logger = logging.getLogger("content_newsroom_live")


def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--topic-file",
        required=True,
        help="Strategy Planner 출력 JSON 파일 경로 (trace 폴더의 03_strategy_planner.json)",
    )
    parser.add_argument("--model", default="gemini-2.0-flash")
    args = parser.parse_args()
    
    # Strategy Planner 출력 로드
    topic_data = json.loads(Path(args.topic_file).read_text(encoding="utf-8"))
    
    # trace 파일 구조에서 output을 추출
    if "output" in topic_data:
        planner_output = topic_data["output"]
    else:
        planner_output = topic_data
    
    if "final_topic" not in planner_output:
        logger.error("입력 파일에 final_topic 없음. Topic Newsroom 결과 파일을 사용하세요.")
        sys.exit(1)
    
    final_topic = planner_output["final_topic"]
    category = final_topic.get("category", "기타")
    
    # Gemini 클라이언트
    client = GeminiClient(model=args.model)
    
    # 에이전트 callable
    agents = build_content_newsroom_agents(client)
    
    # Tracer
    tracer = TraceLogger.new_run(base_dir="runs")
    logger.info(f"Run started: {tracer.run_dir}")
    
    # Content Newsroom 실행 (iter 1만 검증 목적)
    # 실제로는 max 3 iter지만 본 스크립트는 흐름 검증용
    cn = ContentNewsroom(
        tracer=tracer,
        writer_fn=agents["writer"],
        fact_checker_fn=agents["fact_checker"],
        devils_advocate_fn=agents["devils_advocate"],
        editor_fn=agents["editor"],
        base_order=4,
    )
    
    try:
        result = cn.run(category=category, strategy=final_topic)
        status = "completed" if result.get("decision") == "approved" else "partial"
    except Exception as e:
        logger.exception("Content Newsroom 실행 중 예외 발생")
        result = {"error": str(e)}
        status = "failed"
    
    tracer.write_metadata(
        user_input={"category": category, "topic_file": args.topic_file, "model": args.model},
        status=status,
        notes="Step 2.5 조기 LLM 통합 실험 - Content Newsroom",
    )
    
    logger.info(f"Run finished: {tracer.run_dir}")
    logger.info(f"Status: {status}")
    if "final_content" in result:
        logger.info(f"Final title: {result['final_content'].get('title')}")
        logger.info(f"Iterations used: {result.get('iteration')}")
        logger.info(f"Forced: {result.get('_orchestrator_forced', False)}")


if __name__ == "__main__":
    main()
```

---

# 작업 6: .env.example 신규

```
# Google AI Studio API Key
# https://aistudio.google.com/app/apikey 에서 발급
GOOGLE_AI_STUDIO_API_KEY=your_api_key_here
```

`.env` 파일은 만들지 말 것 (사용자가 직접 생성).

---

# 작업 7: 실행 단계 (Claude Code가 직접 수행)

## 7-1. 의존성 설치

```bash
pip install google-generativeai python-dotenv --break-system-packages
```

## 7-2. .env 파일 확인 또는 안내

`.env` 파일이 프로젝트 루트에 있는지 확인. 없으면 사용자에게 안내:

```
.env 파일이 없습니다. 다음 절차로 생성하세요:
1. cp .env.example .env
2. .env 파일을 열어 GOOGLE_AI_STUDIO_API_KEY 값에 실제 API 키 입력
3. https://aistudio.google.com/app/apikey 에서 키 발급 가능
```

API 키 없으면 여기서 중단하고 사용자에게 보고. 다음 단계 진행 금지.

## 7-3. Topic Newsroom 실행

카테고리는 일단 "맛집"으로 고정 (예측 가능한 검증).

```bash
python scripts/run_topic_newsroom_live.py --category 맛집
```

성공 시 `runs/<timestamp>_<run_id>/` 생성. 실패 시 에러 보고 후 다음 단계 진행할지 사용자에게 확인.

## 7-4. Content Newsroom 실행 (Topic 결과 활용)

Topic Newsroom 결과 폴더의 `agents/03_strategy_planner.json`을 입력으로 사용:

```bash
python scripts/run_content_newsroom_live.py --topic-file runs/<topic_run_id>/agents/03_strategy_planner.json
```

성공 시 새 `runs/<timestamp>_<run_id>/` 생성.

---

# 작업 8: docs/early_integration_report.md 신규 (실행 후 작성)

실행 결과를 정리한 보고서 초안. Claude Code가 작성.

```markdown
# Step 2.5 조기 LLM 통합 실행 보고

**실행일**: 2026-05-23  
**목적**: 모의 callable로 검증된 9 prompt + 오케스트레이터를 실제 Gemini로 1회 실행해 통합 이슈 조기 발견

## 실행 결과 요약

### Topic Newsroom
- 카테고리: 맛집
- run_id: <채워넣기>
- 상태: <completed | partial | failed>
- 에이전트 통과 여부:
  - Trend Scout: <✅ / ❌ + 이유>
  - Audience Analyst: <✅ / ❌>
  - Strategy Planner: <✅ / ❌>
- final_topic.title: <채워넣기>
- 총 호출 횟수 / 총 소요 시간 / 추정 비용

### Content Newsroom (iter 1만)
- run_id: <채워넣기>
- 상태: <completed | partial | failed>
- 에이전트 통과 여부:
  - Writer: <✅ / ❌>
  - Fact-Checker: <✅ / ❌>
  - Devil's Advocate: <✅ / ❌>
  - Editor: <✅ / ❌>
- Editor decision: <approved / needs_revision>
- 강제 종료 여부 (_orchestrator_forced): <true / false>
- 총 호출 횟수 / 총 소요 시간

## 발견된 이슈

각 이슈마다 다음 형식으로 기록:

### 이슈 1: <한 줄 요약>
- **에이전트**: <어느 에이전트>
- **현상**: <무엇이 일어났는지>
- **prompt 또는 코드의 어디 문제인지**: <구체적으로>
- **권장 조치**: <prompt 패치 / 오케스트레이터 수정 / 무시>
- **우선순위**: <P0 차단 / P1 중요 / P2 개선>

### 이슈 2: ...

## 일관성 검증 체크리스트

다음 항목을 trace 파일 보면서 확인:

- [ ] 모든 에이전트가 JSON 객체 반환 (텍스트 아님)
- [ ] Trend Scout가 trending_topics 정확히 3개 반환
- [ ] Audience Analyst가 audience_evaluation 입력 순서·개수 유지
- [ ] Strategy Planner가 final_topic 키 모두 채움 (category, title, angle, target_persona, ...)
- [ ] Writer 출력에 fact_claims 배열 있음
- [ ] Fact-Checker 출력의 annotated_draft.sections[].body에 [출처: ...] 마커 박혀있음
- [ ] Fact-Checker confidence_score가 1-10 정수
- [ ] Devil's Advocate critical_issues 개수가 iter 1 = 5개
- [ ] Devil's Advocate pass_threshold가 boolean
- [ ] Editor decision이 "approved" 또는 "needs_revision" 정확히 일치
- [ ] Editor final_content (또는 revision_instructions) 분기 정확

## 다음 단계 권고

- 발견 이슈 P0 차단 건수: <N건>
- prompt 패치 필요 항목: <리스트>
- 오케스트레이터 보강 필요: <리스트>
- Step 3-3 진입 가능 여부: <가능 / 패치 후 가능 / 큰 수정 필요>

## 비용·시간 메모

- 이번 실행 추정 비용: <USD>
- 다음 단계에서 주의할 비용 요소: <Grounding 호출 등>
```

---

# 작업 9: PROGRESS.md 업데이트

## 9-1. Phase 2 체크리스트에 추가 (✅ 처리)

```
- [x] Step 2.5: gemini_client.py + concrete_agents.py + 실행 스크립트 2종 _(2026-05-23)_
- [x] Step 2.5: Topic Newsroom 실제 LLM 1회 실행 _(2026-05-23)_
- [x] Step 2.5: Content Newsroom 실제 LLM 1회 실행 (iter 1) _(2026-05-23)_
- [x] Step 2.5: early_integration_report.md 초안 작성 _(2026-05-23)_
```

## 9-2. 진행률 갱신

- 기존: 32/46 (69.6%)
- 신규: 36/46 (78.3%)

## 9-3. 의사결정 로그 추가

```
- 2026-05-23 묶음 2 Step 2.5 완료 (계획 외 조기 통합 끼워넣기): 실제 Gemini API 통합 1회 검증
  - 목적: Step 3-3 진입 전 LLM 통합 이슈 조기 발견
  - GeminiClient: system_prompt + user_input(dict) → JSON dict. Grounding 옵션 지원.
  - concrete_agents.make_agent_callable: PromptLoader + GeminiClient 결합 → agent_callable
  - 실행 스크립트 2종: Topic Newsroom 1회 + Content Newsroom 1회 (iter 1만)
  - 결정: 모델 분기는 v2로 미루고 Step 2.5는 gemini-2.0-flash 단일 사용
  - early_integration_report.md에 발견 이슈 정리. P0 차단 이슈는 Step 3-3 진입 전 해결.
```

---

# 실행 후 보고 항목

1. 신규 파일 생성 확인 (line count)
   - `backend/llm/__init__.py`, `backend/llm/gemini_client.py`
   - `backend/agents/concrete_agents.py`
   - `scripts/run_topic_newsroom_live.py`, `scripts/run_content_newsroom_live.py`
   - `.env.example`
2. 의존성 설치 결과 (google-generativeai, python-dotenv)
3. **.env 파일 확인 결과** (있음/없음). 없으면 여기서 중단 보고.
4. Topic Newsroom 실행 결과:
   - run_id
   - 상태 (completed/partial/failed)
   - 각 에이전트 통과 여부
   - final_topic.title
5. Content Newsroom 실행 결과:
   - run_id
   - 상태
   - 각 에이전트 통과 여부
   - Editor decision
   - _orchestrator_forced 여부
6. early_integration_report.md 초안 작성 완료 + 발견 이슈 P0/P1/P2 분류
7. PROGRESS.md 진행률 32/46 → 36/46 (78.3%) 갱신 확인
8. git status (스테이징 없음)
9. 다음 단계 안내: 발견 이슈 사용자 검토 후 Step 3-3 진입

---

# 주의사항

- **이번 단계는 실제 API 호출 비용 발생.** Topic 3회 + Content 4회 = 7회 호출. Gemini Flash 가격 기준 매우 저렴 (수십원 수준).
- **.env 미설정 시 절대 진행 금지.** 사용자 컨펌 후 진행.
- 실제 LLM이 출력 형식 안 지키면 그 자체가 이번 단계의 발견. 실패도 의미 있음.
- early_integration_report.md는 발견 사항 그대로 적기. 미화 금지.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

1. **`google-generativeai` 설치 실패**: pip 업데이트 후 재시도. 그래도 실패 시 사용자에게 보고.
2. **Grounding 호출 시 에러**: tools 파라미터 형식이 라이브러리 버전 따라 다를 수 있음. 라이브러리 버전 확인 후 공식 docs 형식 따름.
3. **JSON 파싱 실패 빈발**: gemini_client._parse_json의 추출 로직 개선보다 prompt 자체에 "JSON만 반환, 다른 텍스트 금지" 한 줄 추가를 우선 검토 (단, 본 단계에선 prompt 수정 안 함. early_integration_report.md에 권장사항만 기록).
4. **Topic Newsroom이 실패하면 Content Newsroom 못 돌림**: Topic 결과 없으면 Content 단계는 skip하고 그대로 보고. 강제 가짜 입력 생성 금지.
5. **runs/ 폴더 git 추적 문제**: 본 단계에선 무시. .gitignore 추가는 별도 작업.

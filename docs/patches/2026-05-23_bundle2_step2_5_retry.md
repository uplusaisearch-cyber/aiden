# 묶음 2 Step 2.5 재시도 명세서 — 신규 SDK 기반 LLM 통합

**작성일**: 2026-05-23 (재시도)  
**대상**: Step 2.5 첫 시도 P0 차단 해결 후 재실행  
**범위**: gemini_client.py 재작성 + 호환성 검증 + Topic/Content Newsroom 실제 실행  
**실행 방식**: 코드 재작성 + 의존성 교체 + 실제 LLM 호출 + 결과 보고

---

## 첫 시도 (P0 차단) 회고

첫 시도에서 발견된 P0 3건:

| # | 이슈 | 원인 |
|---|---|---|
| 1 | `gemini-2.0-flash` 404 deprecated | 명세서 모델명 outdated |
| 2 | `"google_search_retrieval"` 400 deprecated | tool API 변경 |
| 3 | grounding tool 호출 불가 | 라이브러리 마이그레이션 필요 |

근본 원인: 명세서가 학습 시점 기준이라 outdated. **이번엔 검색 결과 기반으로 재작성.**

---

## 검색 결과 기반 확정 사항

| 항목 | 신규 |
|---|---|
| 패키지 | `google-genai` (구 `google-generativeai`는 deprecated) |
| 모델 | `gemini-2.5-flash` |
| 클라이언트 | `genai.Client()` |
| Grounding tool | `types.Tool(google_search=types.GoogleSearch())` |
| JSON 강제 | `response_mime_type="application/json"` + `response_schema` |
| ⚠️ **제약** | tools(Grounding) + response_mime_type='application/json' 동시 사용 불가 (API 차단) |

---

## 🔥 핵심 결정: Grounding + JSON 충돌 해결 = 옵션 B

Trend Scout, Fact-Checker (Grounding 사용) 두 에이전트는:
- `response_mime_type` 사용 **안 함**
- prompt에 "JSON만 반환" 명시 (이미 명령 시 추가)
- 응답 파싱은 기존 `_parse_json` (코드블록 제거 + JSON 추출)이 처리
- 실패 시 base_newsroom의 max_retries=1 활용

나머지 7개 에이전트 (Grounding 미사용):
- `response_mime_type="application/json"` 사용
- 더 엄격한 JSON 출력 강제

---

## 본 명세서 작업 개요

| 작업 | 파일 | 작업 종류 |
|---|---|---|
| 1 | `backend/llm/gemini_client.py` | **전체 재작성** |
| 2 | `requirements.txt` 또는 의존성 변경 | google-generativeai 제거 + google-genai 추가 |
| 3 | `backend/agents/concrete_agents.py` | 사실 변경 없음 (인터페이스 동일) |
| 4 | Topic Newsroom 실행 (재시도) | scripts/run_topic_newsroom_live.py 재사용 |
| 5 | Content Newsroom 실행 (재시도) | scripts/run_content_newsroom_live.py 재사용 |
| 6 | `docs/early_integration_report.md` | 재시도 결과 append |
| 7 | `PROGRESS.md` | 의사결정 로그 + 진행률 |

---

# 작업 1: backend/llm/gemini_client.py 전체 재작성

기존 파일 백업 없이 전체 교체. 138줄 → 약 150-180줄.

```python
"""
Gemini API 클라이언트 (google-genai 신규 SDK).

목적: system_prompt + user_input(dict) → JSON dict 반환.
Grounding 옵션 지원 (Trend Scout / Fact-Checker용).

⚠️ 제약: Gemini API는 tools(Grounding) + response_mime_type='application/json' 동시 미지원.
   Grounding 사용 시 mime_type 안 쓰고 prompt 기반 JSON 강제 (옵션 B).

의존: google-genai (구 google-generativeai와 다름)
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None
    logger.warning("google-genai 미설치. pip install google-genai")


# 기본 모델 (2026-05 기준)
DEFAULT_MODEL = "gemini-2.5-flash"

# Grounding 비사용 시 JSON 강제용 추가 지시
JSON_FORCE_SUFFIX = (
    "\n\n출력 형식: 반드시 단일 JSON 객체만 반환하세요. "
    "코드블록(```)이나 JSON 외 텍스트(설명·주석·요약 등)는 절대 포함하지 마세요. "
    "응답의 첫 글자는 `{`, 마지막 글자는 `}`여야 합니다."
)


class GeminiClient:
    """
    google-genai 기반 Gemini API wrapper.
    
    Usage:
        client = GeminiClient(api_key="...", model="gemini-2.5-flash")
        result_dict = client.call(
            system_prompt="...",
            user_input={"category": "맛집"},
            use_grounding=True,
        )
    
    제약:
    - use_grounding=True 일 때 response_mime_type='application/json' 사용 불가
      → prompt에 JSON_FORCE_SUFFIX 추가하여 텍스트 모드에서 JSON 강제
    - use_grounding=False 일 때 response_mime_type='application/json' 사용
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        if genai is None:
            raise RuntimeError("google-genai package not installed")
        
        # GOOGLE_AI_STUDIO_API_KEY (기존) 또는 GEMINI_API_KEY/GOOGLE_API_KEY (SDK 기본) 지원
        self.api_key = (
            api_key
            or os.environ.get("GOOGLE_AI_STUDIO_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "API 키 미설정. .env에 GOOGLE_AI_STUDIO_API_KEY 또는 GEMINI_API_KEY 설정 필요."
            )
        
        self.client = genai.Client(api_key=self.api_key)
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
            ValueError: JSON 파싱 실패 시
        """
        # user_input을 JSON 문자열로 직렬화해 전달
        user_message = (
            "다음 JSON 입력을 받아 system prompt의 출력 형식에 정확히 맞는 JSON만 반환해주세요.\n\n"
            f"입력:\n```json\n{json.dumps(user_input, ensure_ascii=False, indent=2)}\n```"
        )
        
        # 시스템 프롬프트 조립
        effective_system_prompt = system_prompt
        if use_grounding:
            # Grounding 사용 시 mime_type 못 박으므로 prompt로 JSON 강제
            effective_system_prompt = system_prompt + JSON_FORCE_SUFFIX
        
        # config 조립
        config_kwargs: dict[str, Any] = {
            "system_instruction": effective_system_prompt,
            "temperature": temperature,
        }
        
        if use_grounding:
            # Grounding tool 추가, mime_type 미사용
            config_kwargs["tools"] = [
                types.Tool(google_search=types.GoogleSearch())
            ]
        else:
            # JSON 모드
            config_kwargs["response_mime_type"] = "application/json"
        
        config = types.GenerateContentConfig(**config_kwargs)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config=config,
            )
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise
        
        raw_text = self._extract_text(response)
        return self._parse_json(raw_text)
    
    @staticmethod
    def _extract_text(response) -> str:
        """response 객체에서 text 추출. Grounding 시 candidates 구조가 다를 수 있음."""
        # 1순위: response.text (대부분 케이스)
        text = getattr(response, "text", None)
        if text:
            return text
        
        # 2순위: candidates[0].content.parts[*].text 합치기
        try:
            candidates = getattr(response, "candidates", None) or []
            if candidates:
                parts = candidates[0].content.parts
                texts = [getattr(p, "text", "") for p in parts]
                joined = "".join(t for t in texts if t)
                if joined:
                    return joined
        except Exception as e:
            logger.warning(f"Failed to extract text from candidates: {e}")
        
        return ""
    
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

# 작업 2: 의존성 교체

## 2-1. 패키지 제거 + 설치

```bash
pip uninstall google-generativeai -y
pip install google-genai python-dotenv --break-system-packages
```

## 2-2. requirements.txt 확인 또는 생성

`requirements.txt` 파일이 있으면 다음 라인 수정:
- 제거: `google-generativeai`
- 추가: `google-genai`

없으면 생성하지 말고 보고만 (별도 작업에서 처리).

## 2-3. 설치 확인

```bash
python -c "from google import genai; print(genai.__version__ if hasattr(genai, '__version__') else 'installed')"
```

성공해야 함. 실패 시 사용자에게 보고.

---

# 작업 3: backend/agents/concrete_agents.py 검토

기존 파일 인터페이스 유지. `make_agent_callable`이 GeminiClient 호출하는 부분만 동작 확인.

**변경 필요 없음.** GeminiClient의 `call()` 시그니처가 동일하므로 concrete_agents는 그대로 동작해야 함.

다만 다음 사항 점검:
- `make_agent_callable` 시그니처: `use_grounding` 인자 그대로
- 호출부 `llm_client.call(system_prompt=..., user_input=..., use_grounding=...)` 변경 없음

검토 후 변경 없으면 보고에 "concrete_agents.py 변경 없음" 명시.

---

# 작업 4: .env 변수명 호환 확인

기존 `.env`에 `GOOGLE_AI_STUDIO_API_KEY=AIza...` 설정되어 있음.  
신규 GeminiClient는 `GOOGLE_AI_STUDIO_API_KEY` / `GEMINI_API_KEY` / `GOOGLE_API_KEY` 셋 다 인식하므로 **변경 불필요.**

확인만 하고 진행.

---

# 작업 5: Topic Newsroom 실제 실행 (재시도)

기존 `scripts/run_topic_newsroom_live.py` 그대로 사용.

```bash
python scripts/run_topic_newsroom_live.py --category 맛집
```

성공/실패 모두 trace 생성됨. `runs/<timestamp>_<run_id>/` 확인.

## 5-1. 실행 후 확인 체크리스트

trace 파일들을 보면서 다음 확인:

- [ ] `runs/<run_id>/agents/01_trend_scout.json` 의 `output` 필드에 `trending_topics` 배열 있음
- [ ] `trending_topics` 길이가 정확히 3
- [ ] 각 topic에 `sources` 배열, `longevity` 값 있음
- [ ] `runs/<run_id>/agents/02_audience_analyst.json` 의 `output` 필드에 `audience_evaluation` 배열 있음
- [ ] `verdict.top_choice_topic` 이 `trending_topics`의 topic 중 하나와 일치
- [ ] `runs/<run_id>/agents/03_strategy_planner.json` 의 `output` 필드에 `final_topic` 있음
- [ ] `final_topic.category`, `title`, `key_messages`, `data_grounding` 모두 채워짐

체크리스트 결과 보고에 포함.

## 5-2. 실행 실패 시 처리

- Trend Scout 단계 실패 → 신규 SDK 호환성 추가 검증 필요. trace의 error 메시지 그대로 보고.
- Audience/Planner 단계 실패 → JSON 출력 안 지켰을 가능성. raw output 보고.
- 두 번째 시도도 실패하면 중단하고 사용자 보고.

---

# 작업 6: Content Newsroom 실제 실행 (Topic 결과 활용)

Topic Newsroom 성공 시에만 진행. 실패 시 skip.

```bash
python scripts/run_content_newsroom_live.py --topic-file runs/<topic_run_id>/agents/03_strategy_planner.json
```

⚠️ **비용 주의**: Content Newsroom은 iter 1만 돌려도 Writer/FC/DA/Editor 4회 호출. iter 2/3 가면 더 많음. 명세서대로 iter 1만 확인 목적.

## 6-1. 실행 후 확인 체크리스트

- [ ] `runs/<content_run_id>/agents/04_writer_iter1.json` 의 `output`에 `sections` 배열, 각 섹션에 `fact_claims` 있음
- [ ] `runs/<content_run_id>/agents/05_fact_checker_iter1.json` 의 `output`에 `verification_log`, `annotated_draft` 있음
- [ ] `annotated_draft.sections[].body`에 `[출처: ...]` 마커 박혀있음 (확률적, 없을 수도 있음 → P1 이슈)
- [ ] `runs/<content_run_id>/agents/06_devils_advocate_iter1.json` 의 `output`에 `critical_issues` 5개
- [ ] `runs/<content_run_id>/agents/07_editor_iter1.json` 의 `output`에 `decision` (값: "approved" 또는 "needs_revision")
- [ ] Editor가 needs_revision이면 iter 2 자동 진행됨 (orchestrator 동작 확인)

## 6-2. 비용 메모

대략 추정 (gemini-2.5-flash 가격 기준):
- Topic: 3 호출 ≈ $0.001 미만
- Content iter 1: 4 호출 ≈ $0.002 미만
- 최악 iter 3까지: 4×3 = 12 호출 ≈ $0.005 미만

총 1센트 미만. 무시 가능.

---

# 작업 7: docs/early_integration_report.md 재시도 결과 append

기존 보고서 끝에 다음 섹션 추가:

```markdown
---

## 재시도 결과 (2026-05-23 두 번째 시도)

### 변경 사항
- 패키지: google-generativeai → google-genai
- 모델: gemini-2.0-flash → gemini-2.5-flash
- Grounding tool: "google_search_retrieval" 문자열 → types.Tool(google_search=types.GoogleSearch())
- Grounding 사용 시 response_mime_type 미사용, prompt 기반 JSON 강제 (옵션 B)

### Topic Newsroom 실행 결과
- run_id: <채워넣기>
- 상태: <completed | partial | failed>
- 각 에이전트 통과: Scout <✅/❌>, Analyst <✅/❌>, Planner <✅/❌>
- final_topic.title: <채워넣기>

### Content Newsroom 실행 결과 (iter 1)
- run_id: <채워넣기>
- 상태: <completed | partial | failed>
- 각 에이전트 통과: Writer <✅/❌>, FC <✅/❌>, DA <✅/❌>, Editor <✅/❌>
- Editor decision: <approved | needs_revision>

### 재시도에서 발견된 이슈
(첫 시도 P0 3건은 모두 해소됨. 본 섹션은 신규 발견 이슈만 기록.)

(이슈가 있으면 형식대로 기록, 없으면 "신규 P0 차단 이슈 없음" 명시)

### 일관성 검증 체크리스트 결과
(작업 5-1, 6-1의 체크리스트 결과 그대로)

### Step 3-3 진입 가능 여부
- 신규 P0 차단 0건이면 → 진입 가능
- 1건 이상이면 → 해결 후 진입

### 학습 내용 (회고)
- SDK 마이그레이션 시 명세서 작성 전 반드시 최신 docs 확인
- Grounding + JSON 강제 충돌은 API 레벨 제약이며 우회 패턴 필요
- 조기 통합(Step 2.5)이 없었으면 Step 3-3까지 다 만들고 발견했을 것
```

---

# 작업 8: PROGRESS.md 업데이트

## 8-1. Phase 2 체크리스트 패치

기존 항목 중 ❌로 표시됐던 것들:
- Step 2.5: Topic Newsroom 실제 LLM 실행 → ✅ (성공 시) 또는 ❌ 유지 (실패 시)
- Step 2.5: Content Newsroom 실제 LLM 실행 → 동일

상태에 따라 갱신.

## 8-2. 진행률

- 첫 시도 후: 33/46 (71.7%)
- 재시도 성공 시: 36/46 (78.3%) — 첫 시도 명세 그대로 회복
- 재시도 부분 성공 시: 그 사이 값

## 8-3. 의사결정 로그 추가

```
- 2026-05-23 묶음 2 Step 2.5 재시도: 신규 SDK 마이그레이션
  - 패키지: google-generativeai → google-genai
  - 모델: gemini-2.0-flash → gemini-2.5-flash
  - Grounding tool: types.Tool(google_search=types.GoogleSearch()) 패턴 적용
  - Grounding + JSON 충돌 해결: 옵션 B (prompt 기반 JSON 강제) 채택
  - 결과: <성공/부분성공/실패>
  - 신규 P0 차단 이슈: <0건/N건>
  - 학습: SDK 마이그레이션은 명세서 작성 전 최신 docs 검증 필수
```

---

# 실행 후 보고 항목

1. gemini_client.py 재작성 확인 (line count + 핵심 변경점)
2. 의존성 교체 결과 (google-generativeai 제거, google-genai 설치)
3. concrete_agents.py 변경 여부 (변경 없으면 "변경 없음")
4. Topic Newsroom 실행 결과:
   - run_id
   - 상태
   - 각 에이전트 통과 여부
   - 일관성 검증 체크리스트 (작업 5-1) 결과
5. Content Newsroom 실행 결과 (Topic 성공 시에만):
   - run_id
   - 상태
   - 각 에이전트 통과 여부
   - 일관성 검증 체크리스트 (작업 6-1) 결과
   - Editor decision + iter 진행 상황
6. 비용 추정 (총 호출 횟수 + 추정 USD)
7. early_integration_report.md append 확인
8. PROGRESS.md 진행률 갱신 확인
9. git status (스테이징 없음)
10. 다음 단계 안내:
    - 신규 P0 차단 0건 → Step 3-3 진입 가능
    - 1건 이상 → 사용자 검토 후 결정

---

# 주의사항

- **이번엔 실제 API 호출이 정상 동작해야 함.** 첫 시도 같은 SDK/모델 에러 다시 나면 즉시 중단 보고.
- 첫 시도의 runs/ 폴더 4개는 그대로 둠 (이력 보존).
- early_integration_report.md는 첫 시도 내용 보존하고 끝에 append (덮어쓰지 말 것).
- 실제 LLM 출력에서 발견된 이슈는 미화 없이 기록.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

---

# 의문사항 발생 시 처리

1. **google-genai 설치 실패**: pip 캐시 정리 후 재시도. 그래도 실패하면 사용자에게 보고.
2. **types.Tool(google_search=...) 거부**: 라이브러리 버전 확인. `pip show google-genai`로 버전 출력 후 사용자 보고.
3. **response.text가 비어있음 (Grounding 시)**: `_extract_text` 메서드가 candidates 구조 처리. 그래도 비어있으면 raw response 객체 dict로 변환해 trace에 기록.
4. **Topic Newsroom 성공, Content Newsroom 실패**: 사용자에게 보고 후 결정 대기. 강제 진행 금지.
5. **JSON 파싱 빈발 실패**: prompt에 JSON_FORCE_SUFFIX 추가했음에도 실패하면 P1 이슈로 기록. 우회책은 다음 단계에서 검토.

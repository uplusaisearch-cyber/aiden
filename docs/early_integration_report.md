# Step 2.5 조기 LLM 통합 실행 보고

**실행일**: 2026-05-25 (명세서 작성일 2026-05-23)
**목적**: 모의 callable 로 검증된 9 prompt + 오케스트레이터를 실제 Gemini 로 1회 실행해 통합 이슈 조기 발견
**결론**: **P0 차단 이슈 1건 발견. Step 3-3 진입 전 라이브러리 마이그레이션 필요.**

---

## 실행 결과 요약

### 시도 횟수

총 4회 시도, 모두 Trend Scout 단계에서 실패. **단 한 번도 Audience Analyst 이후로 진행하지 못함.**

| # | 모델 | tools 인자 | 결과 | run_id |
|---|---|---|---|---|
| 1 | `gemini-2.0-flash` (명세서 default) | `"google_search_retrieval"` 문자열 | 404 model deprecated | `2026-05-25T05-22-07_cc7077bf` |
| 2 | `gemini-2.5-flash` | `"google_search_retrieval"` 문자열 | 400 tool deprecated | `2026-05-25T05-22-38_f006457f` |
| 3 | `gemini-2.5-flash` | `"google_search"` 문자열 | ValueError (라이브러리가 string tool은 'code_execution' 만 허용) | `2026-05-25T05-22-59_d23c6734` |
| 4 | `gemini-2.5-flash` | `[{"google_search": {}}]` dict | ValueError (FunctionDeclaration에 google_search 필드 없음) | `2026-05-25T05-23-38_10afa0e4` |

### Topic Newsroom

- 카테고리: 맛집
- **상태: failed (단 한 번도 Trend Scout 통과 못함)**
- 에이전트 통과 여부:
  - Trend Scout: ❌ (모델/툴 호환성 문제로 호출 자체 실패)
  - Audience Analyst: 미실행
  - Strategy Planner: 미실행
- final_topic.title: **없음**
- 총 호출 횟수: API 도달 2건(시도 1, 2) + 라이브러리 거부 2건(시도 3, 4) × 각 2회 재시도 = API 실제 호출 4건, 라이브러리 거부 4건
- 추정 비용: ~$0 (모두 generation 도달 전 실패)

### Content Newsroom (iter 1만)

**미실행.** 사용자 지시 "Topic Newsroom 실패해도 Content Newsroom은 강제 진행하지 말 것"에 따름.

---

## 발견된 이슈

### 이슈 1: `gemini-2.0-flash` 모델이 신규 사용자에게 차단됨
- **에이전트**: 전체 (모델 기본값)
- **현상**: `404 This model models/gemini-2.0-flash is no longer available to new users.`
- **위치**: `backend/llm/gemini_client.py` 생성자 default `model="gemini-2.0-flash"` (명세서 작업 2 그대로)
- **권장 조치**: 기본값을 `gemini-2.5-flash`로 변경. 명세서 자체 업데이트 필요.
- **우선순위**: **P0 차단**

### 이슈 2: `google-generativeai` 패키지가 deprecated 상태
- **에이전트**: 전체
- **현상**: import 시 `FutureWarning: All support for the google.generativeai package has ended. ... Please switch to the google.genai package as soon as possible.`
- **위치**: `backend/llm/gemini_client.py` line 18 `import google.generativeai as genai`
- **권장 조치**: `google-genai` (신규 패키지) 로 마이그레이션. API 표면이 완전히 다름 (`genai.Client(api_key=...)`, `client.models.generate_content(...)` 등). gemini_client.py 사실상 재작성.
- **우선순위**: **P0 차단** (이슈 3과 연결됨)

### 이슈 3: Gemini 2.5 의 Grounding(`google_search`) tool 을 deprecated 라이브러리에서 호출 불가
- **에이전트**: Trend Scout, Fact-Checker (둘 다 grounding 사용)
- **현상**: 4가지 형식 모두 거부됨
  1. `"google_search_retrieval"` 문자열 → Gemini 2.5 API가 거부 (`400 ... Please use google_search tool instead`)
  2. `"google_search"` 문자열 → 라이브러리 거부 (`The only string that can be passed as a tool is 'code_execution'`)
  3. `[{"google_search": {}}]` dict → 라이브러리가 FunctionDeclaration 으로 해석하려다 거부 (`Unknown field for FunctionDeclaration: google_search`)
  4. (시도 안 함) `genai.protos.Tool(google_search=...)` → 라이브러리 protos 에 GoogleSearch 메시지 자체가 정의되어 있을 가능성 낮음 (deprecated 라이브러리)
- **위치**: `backend/llm/gemini_client.py` `call()` 메서드의 `tools` 구성 (현재 4번째 시도 형식이 남아있음)
- **권장 조치**: `google-genai` 신규 패키지로 마이그레이션. 신규 패키지에서는 다음 형식 지원:
  ```python
  from google.genai import types
  config = types.GenerateContentConfig(
      tools=[types.Tool(google_search=types.GoogleSearch())]
  )
  ```
  현재 deprecated 라이브러리로는 사실상 우회 경로 없음.
- **우선순위**: **P0 차단**

### 이슈 4: 명세서가 deprecated 라이브러리·deprecated 모델을 명시
- **에이전트**: -
- **현상**: 명세서 작업 1, 2가 `google-generativeai` + `gemini-2.0-flash` 고정. 명세서 작성 시점(2026-05-23)에 이미 양쪽 deprecated. 짧은 시간 안에 deprecated 처리됐을 수도 있음.
- **권장 조치**: 명세서 자체를 업데이트해서 `google-genai` + `gemini-2.5-flash` 기준으로 재작성. 사용자 검토 필요.
- **우선순위**: **P1 중요**

### 이슈 5: 시도 3에서 라이브러리가 string tool 을 FunctionDeclaration으로 잘못 해석
- **에이전트**: -
- **현상**: dict `{"google_search": {}}` 를 함수 선언으로 잘못 해석 → google_search 라는 함수가 없으니 거부
- **위치**: `google-generativeai 0.8.6` 패키지 내부
- **권장 조치**: 라이브러리 한계. 이슈 2·3 해결로 자동 사라짐.
- **우선순위**: **P2 개선 (정보)**

---

## 일관성 검증 체크리스트

**모두 미검증.** Trend Scout 가 호출조차 못 되어 출력 자체가 없음.

- [ ] 모든 에이전트가 JSON 객체 반환 (텍스트 아님) — **N/A**
- [ ] Trend Scout 가 trending_topics 정확히 3개 반환 — **N/A**
- [ ] Audience Analyst 가 audience_evaluation 입력 순서·개수 유지 — **N/A**
- [ ] Strategy Planner 가 final_topic 키 모두 채움 — **N/A**
- [ ] Writer 출력에 fact_claims 배열 있음 — **N/A**
- [ ] Fact-Checker 출력의 annotated_draft.sections[].body 에 `[출처: ...]` 마커 박혀있음 — **N/A**
- [ ] Fact-Checker confidence_score 가 1-10 정수 — **N/A**
- [ ] Devil's Advocate critical_issues 개수가 iter 1 = 5개 — **N/A**
- [ ] Devil's Advocate pass_threshold 가 boolean — **N/A**
- [ ] Editor decision 이 "approved" 또는 "needs_revision" 정확히 일치 — **N/A**
- [ ] Editor final_content (또는 revision_instructions) 분기 정확 — **N/A**

---

## 다음 단계 권고

- 발견 이슈 P0 차단 건수: **3건** (이슈 1, 2, 3)
- prompt 패치 필요 항목: **없음** (prompt 자체는 아직 호출되지 못함, 검증 보류)
- 오케스트레이터 보강 필요: **없음** (현 코드는 LLM 실패 시 `_force_approve` 로 graceful degrade 정상 동작 확인됨 — 이건 의도된 동작)
- **Step 3-3 진입 가능 여부: 큰 수정 필요** — `backend/llm/gemini_client.py` 재작성 (deprecated 라이브러리 → `google-genai`) 후 재검증 필요

### 추천 후속 작업 (사용자 결정 필요)

1. **방안 A — 라이브러리 마이그레이션 (권장)**:
   - `pip install google-genai`
   - `gemini_client.py` 를 `from google import genai` 기반으로 재작성
   - `tools=[types.Tool(google_search=types.GoogleSearch())]` 사용
   - 모델 기본값 `gemini-2.5-flash` 로 변경
   - Step 2.5 재실행

2. **방안 B — Grounding 비활성화한 채 프롬프트 검증 (보조)**:
   - Trend Scout 와 Fact-Checker 에 `use_grounding=False` 강제
   - Scout 은 환각 결과를 내겠지만, **JSON 스키마 일치·키 이름·이상값 발견은 가능**
   - prompt 단의 P0 차단 이슈를 미리 잡을 수 있음
   - 마이그레이션 작업 전·후 비교 가능
   - 비용 매우 작음 (~$0)

3. **방안 C — 이번 단계 보류**: Step 2.5 를 v2 로 미루고 Step 3-3 진입 (모의 callable 로만 검증). 위험 — 통합 단계에서 추가 P0 발견 시 prompt 다 손봐야 함.

---

## 비용·시간 메모

- 이번 실행 추정 비용: **~$0**
  - API 도달 후 generation 시작 전 실패가 대부분
  - 실제 token 생성된 호출 없음
- 다음 단계에서 주의할 비용 요소:
  - 마이그레이션 후 재실행 시: Topic 3회 + Content 4회 + grounding 호출은 정상 진행 시 일부 추가 비용
  - Gemini 2.5 Flash 기준 여전히 수십원 수준

---

## 작업 중 변경된 파일

- `backend/llm/gemini_client.py`: `tools` 인자 4번 수정 (명세서 그대로 → `"google_search"` → `[{"google_search": {}}]`). **현재 4번째 시도 상태로 남아있음.** 마이그레이션 시 어차피 재작성 필요.
- `runs/` 폴더: 4개 run 폴더 생성 (모두 partial 상태).

---

## 트레이스 예시 (시도 4 — 가장 깔끔한 실패)

`runs/2026-05-25T05-23-38_10afa0e4/agents/01_trend_scout.json`:
```json
{
  "order": 1,
  "agent_name": "trend_scout",
  "iteration": null,
  "duration_ms": 501,
  "input": {
    "category": "맛집",
    "target_date": "2026-05-25"
  },
  "output": {},
  "error": "ValueError: Unknown field for FunctionDeclaration: google_search"
}
```

오케스트레이터의 trace 기록은 정상 동작 (입력·에러 메시지·duration 모두 보존됨).

---

## 재시도 결과 (2026-05-25 두 번째 시도)

### 변경 사항
- 패키지: `google-generativeai 0.8.6` → `google-genai 2.6.0`
- 모델: `gemini-2.0-flash` → `gemini-2.5-flash` (DEFAULT_MODEL 상수 + 스크립트 default 양쪽)
- Grounding tool: `"google_search_retrieval"` 문자열 → `types.Tool(google_search=types.GoogleSearch())`
- Grounding 사용 시 `response_mime_type` 미사용, prompt 기반 JSON 강제 (옵션 B, `JSON_FORCE_SUFFIX` 추가)
- `genai.Client(api_key=...).models.generate_content(...)` 신규 SDK 패턴
- `_extract_text()` 추가 — Grounding 시 `response.text` 비어있을 경우 `candidates[0].content.parts` fallback

### Topic Newsroom 실행 결과
- **run_id**: `2026-05-25T05-52-32_4c4f0b29`
- **상태**: **completed** ✅
- 각 에이전트 통과: Scout ✅ / Analyst ✅ / Planner ✅
- final_topic.title: **"편의점 신상 디저트, 우리 가족 최애템 TOP5"**
- final_topic.category: 맛집
- final_topic.target_persona: "주말에 아이와 함께 즐길 만한 간식을 찾는 30대 맞벌이 부모"
- content_type_recommendation: A

### Content Newsroom 실행 결과 (iter 1 → 2 → 3 → approved)
- **run_id**: `2026-05-25T05-53-50_7eba2b37`
- **상태**: **completed** ✅ (Editor 자체 approved, orchestrator coerce 안 일어남)
- 각 에이전트 통과: Writer ✅ / FC ✅ / DA ✅ / Editor ✅ (모든 iter)
- Editor decision 흐름: iter1 `needs_revision` → iter2 `needs_revision` → iter3 `approved`
- `_orchestrator_forced`: false
- `_orchestrator_coerced_at_iter3`: false (Editor 가 자체 approved)
- **iter 진행** (요약 highlight 그대로):
  - iter 1: Writer 5 sections / FC confidence=8, verified=5/6 / DA 5 critiques avg 3.6 pass=False / Editor accepted=5
  - iter 2: Writer 5 sections / FC confidence=9, verified=2/3 / DA 3 critiques avg 6.2 pass=False / Editor accepted=3
  - iter 3: Writer 5 sections / FC confidence=10, verified=0/0 / DA 1 critique avg 6.6 pass=True / Editor accepted=1 → approved

### 재시도에서 발견된 이슈

#### 이슈 R1: 첫 시도 P0 3건 모두 해소됨 ✅
신규 SDK + 모델 + 옵션 B (Grounding+JSON 분리 처리) 조합으로 통합 정상 동작.

#### 이슈 R2: 한 번의 503 Service Unavailable (P3, 정보)
- **에이전트**: Fact-Checker iter 2 (첫 호출)
- **현상**: Gemini API 503 "high demand". `base_newsroom._execute_agent` retry(0.5s 백오프) 후 정상 응답.
- **권장 조치**: 현 retry 로직(`max_retries=1`)이 정상 흡수. 추가 대응 불요. 다만 본격 운영 시 지수 백오프로 강화 권장.
- **우선순위**: **P3 정보** (정상 처리됨)

#### 이슈 R3: FC iter 3 의 verification_log 가 0건 (P2 관찰)
- **현상**: iter 3 Writer 출력에 fact_claims 가 없거나, FC 가 검증할 claim 이 없다고 판단. `verification_log=[]`, `verified=0/0`, `confidence=10` (자동 max?).
- **위치**: `04_writer.md` 또는 `05_fact_checker.md` prompt. iter 3 에서 Writer 가 fact_claims 를 비웠을 수 있음.
- **권장 조치**: Writer prompt 에 "iter N+ 에서도 fact_claims 유지" 명시 점검. 본 단계에선 prompt 수정 없이 관찰만.
- **우선순위**: **P2 관찰** (출력 품질 영향 가능, 차단 아님)

#### 이슈 R4: 학습 — 검색 결과 기반 명세 작성의 중요성 (회고)
첫 시도가 학습 시점 기준으로 작성된 명세서를 그대로 따라가다 P0 차단 3건. 재시도는 검색 결과 기반으로 작성된 명세서로 단번에 통과. **SDK·모델·API 표면처럼 빠르게 변하는 부분은 명세서 작성 시 반드시 최신 docs 확인.**

### 일관성 검증 체크리스트 결과

**Topic Newsroom (§5-1)**:
- [x] 모든 에이전트가 JSON 객체 반환
- [x] Trend Scout trending_topics 정확히 3개
- [x] 각 topic 에 sources, longevity 있음 (3개 모두 evergreen)
- [x] Audience Analyst audience_evaluation 3개, 순서 유지
- [x] verdict.top_choice_topic 이 trending_topics 중 하나와 정확 일치
- [x] Strategy Planner final_topic 키 모두 채워짐 (category·title·angle·target_persona·content_type_recommendation·key_messages·data_grounding 누락 없음)

**Content Newsroom (§6-1)**:
- [x] Writer iter1: sections 5개, 모든 섹션에 fact_claims 배열
- [x] Fact-Checker iter1: verification_log 6 items, annotated_draft.sections[].body 에 `[출처: ...]` 마커 박혀있음
- [x] Fact-Checker confidence_score 가 1-10 정수
- [x] Devil's Advocate iter1: critical_issues 정확히 5개, pass_threshold 가 bool
- [x] Editor decision 이 `"approved"` 또는 `"needs_revision"` enum 정확 일치
- [x] needs_revision 시 iter 2 자동 진행됨 (orchestrator 동작 확인) — iter 1·2 모두 needs_revision, iter 3 에서 자체 approved

### 비용 추정
- Topic Newsroom: 3 호출 (Scout grounded, Analyst, Planner)
- Content Newsroom: iter 1(4) + iter 2(4+1 retry) + iter 3(4) = 13 호출
- **총 16 호출 (gemini-2.5-flash)**. 모두 generation 정상 도달.
- 추정 비용: **~$0.005-0.015** (수십원 수준). 503 retry 포함.

### Step 3-3 진입 가능 여부
- **신규 P0 차단: 0건**
- **P1 중요: 0건**
- P2 관찰 1건 (R3 — FC iter 3 verification_log 비어있음), P3 정보 1건 (R2 — 503 일시 retry)
- **→ Step 3-3 (Game-ifier + 전체 통합) 진입 가능**

### 학습 내용 (회고)
- SDK 마이그레이션 시 명세서 작성 전 반드시 최신 docs 확인 (학습 컷오프 기준 명세는 outdated 위험)
- Grounding + `response_mime_type=application/json` 충돌은 Gemini API 레벨 제약. 옵션 B(prompt 기반 JSON 강제)가 깔끔히 동작.
- 조기 통합(Step 2.5)이 없었으면 Step 3-3 전체 통합 후 발견했을 것 → prompt 9개 + 오케스트레이터 다 손봐야 했음. **조기 발견 = 큰 절약.**
- Content Newsroom 의 토론 라운드별 차등(DA 5→3→1, avg score 3.6→6.2→6.6, pass False→False→True) 이 실제 LLM 환경에서도 정상 작동 확인.

---

## Step 3-3 E2E 9 에이전트 완주 (2026-05-25)

### 실행 결과
- **run_id**: `2026-05-25T06-16-20_1bc88d21`
- 카테고리: 맛집
- **상태: completed** ✅
- duration_sec: 372 (약 6분 12초)
- step_count: 17 (Stage 1: 3 + Stage 2: 12 [iter 1·2·3 × 4 에이전트] + Stage 3: 2)
- 9 에이전트 통과:
  - 01 Trend Scout ✅ (3 topics, 모두 evergreen)
  - 02 Audience Analyst ✅ (top: "가성비·가심비 외식 및 집밥 경제")
  - 03 Strategy Planner ✅ (title: "가성비·가심비 외식 & 집밥: 현명한 식비 절약 가이드")
  - 04 Writer (iter 3) ✅
  - 05 Fact-Checker (iter 3) ✅
  - 06 Devil's Advocate (iter 3, pass=True) ✅
  - 07 Editor (final iter 3, decision=approved) ✅
  - 08 Format Architect ✅ (**type=C, base=A, interactive=CALCULATOR**)
  - 09 HTML Builder ✅ (3 subs, 0 preserved, 0 warnings)
- 최종 산출물: `runs/2026-05-25T06-16-20_1bc88d21/final_output.html` (6,664 bytes)
- 총 호출 횟수: **18회** (17 trace + 1 503 retry 흡수)
- 추정 비용: **~$0.015-0.025** (수십원 수준)

### Stage 2 토론 흐름 (iter 1 → 3 자체 approved)
| iter | Writer | FC | DA | Editor |
|---|---|---|---|---|
| 1 | 3 sections | confidence=10, verified=2/2 | 5 critiques, avg=4.0, pass=False | needs_revision (accepted=5) |
| 2 | 3 sections | confidence=10, verified=4/4 | 3 critiques, avg=7.0, pass=False | needs_revision (accepted=3) |
| 3 | 3 sections | confidence=10, verified=0/0 | 1 critique, avg=5.8, pass=True | **approved** (accepted=1) |

→ `_orchestrator_coerced_at_iter3 == False` (Editor 자체 approved, orchestrator 강제 안 일어남)

### 브라우저 검증용 사전 체크 (HTML 구조)
- `<meta charset="utf-8">`: ✅ 있음
- mathjs CDN (`mathjs`): ✅ 포함됨
- CALCULATOR DOM (`data-input-id`, `data-result`, `calc-container`): ✅ 모두 존재
- `<script>` 태그 2개 (mathjs + init): ✅
- `plustab-interactive` 클래스: ✅
- `[출처: ...]` inline 마커: **5개 발견**
- 한국어 인코딩: ✅ (예: "식비", "50만원" 모두 보존)
- 제목: "가족 식비, 매달 50만원 아끼는 법"
- 섹션 3개 / 출처 8개 / known_weaknesses 0건

### 발견 이슈 (Step 3-3 신규)
- **신규 P0 차단: 0건**
- **P1 중요: 0건**
- **P2 관찰 (재발 확인)**: FC iter 3 `verification_log=[]`, verified=0/0, confidence=10 — Step 2.5 재시도에서 발견한 R3 패턴 재현. Writer iter 3 출력에서 fact_claims 가 비워지는 경향. 별도 prompt 패치 검토 권장.
- **P3 정보**: DA iter 1 첫 호출에서 503 Service Unavailable 1회 → `base_newsroom._execute_agent` retry(0.5s)로 정상 흡수. Step 2.5 와 동일 패턴.

### Step 3-3 진입 후 회고
- **9 에이전트 첫 완주 의미**: AIDEN 의 핵심 워크플로(뉴스룸 토론 → 사실 검증 → 형식 결정 → HTML 생성)가 실제 LLM 환경에서 end-to-end 동작함을 첫 검증. Format Architect 가 식비 절약 주제에 **CALCULATOR** 인터랙티브를 선택한 점은 prompt 의 의도가 LLM 으로도 전달됨을 보여줌.
- **묶음 3 진입 가능 여부**: **가능**. CLI E2E 동작 확인. UI(FastAPI/Next.js) 부착이 다음 단계.
- **발표용 메타 산출물 1호 확보**: ✅ `runs/2026-05-25T06-16-20_1bc88d21/` 전체 — final_output.html + 17 trace + summary.jsonl + metadata.json 일습. 발표 시 9 에이전트 토론 과정 시각화 가능.

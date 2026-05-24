# 묶음 2 Step 1 검토 패치 명령서

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 2 Step 1 (4개 prompt) 검토 후속 패치  
**범위**: 13건 prompt 패치 + NEXT_BUNDLE_NOTES.md 메모 3건 + PROGRESS.md 업데이트  
**실행 방식**: 코드 실행/테스트 없이 파일 편집만

---

## 작업 개요

| 작업 | 파일 | 변경 건수 |
|---|---|---|
| 1 | `backend/agents/prompts/01_trend_scout.md` | 3건 |
| 2 | `backend/agents/prompts/02_audience_analyst.md` | 2건 |
| 3 | `backend/agents/prompts/03_strategy_planner.md` | 4건 |
| 4 | `backend/agents/prompts/09_html_builder.md` | 4건 |
| 5 | `docs/NEXT_BUNDLE_NOTES.md` | 3개 항목 추가 (§7) |
| 6 | `PROGRESS.md` | 의사결정 로그 + 이슈 |

**총 13건 패치 + 메모 3건 + 진행상황 갱신**

---

## 검토 시 적용된 default 결정 (수정에 반영)

- `estimated_volume` 유지 (Strategy Planner 의사결정엔 안 쓰이지만 어드민 표시·향후 활용 여지)
- `target_date`는 검색 쿼리 작성 + 출처 컷오프 기준에 활용
- `audience_analyst.angle_suggestion`은 유지, Strategy Planner가 우선 참고하도록 03에 규칙 추가
- mathjs CDN 버전 12.4.2 유지 (config 분리는 Step 2 메모)

---

# 작업 1: backend/agents/prompts/01_trend_scout.md

## 1-1. 검색 절차 1번에 target_date 활용 명시

### BEFORE

````
## 검색 절차 (반드시 따를 것)
1. category 기반으로 2-3개의 검색 쿼리 작성 (예: "맛집" → "2026년 5월 핫플 맛집", "최근 인기 맛집 트렌드", "신상 맛집")
````

### AFTER

````
## 검색 절차 (반드시 따를 것)
1. category 기반으로 2-3개의 검색 쿼리 작성. **`target_date` 기준 최근 30일 이내 결과 우선.** 예: target_date=2026-05-23 → "2026년 5월 핫플 맛집", "최근 인기 맛집 트렌드", "신상 맛집"
````

---

## 1-2. 입력 스키마에 자유 입력 category 처리 명시

### BEFORE

````
## 입력
```json
{
  "category": "맛집|AI트렌드|안전|문화|기타 (또는 자유 입력)",
  "target_date": "2026-05-23"
}
```
````

### AFTER

````
## 입력
```json
{
  "category": "맛집|AI트렌드|안전|문화|기타 (또는 자유 입력)",
  "target_date": "2026-05-23"
}
```

**category 자유 입력 케이스**: 매핑 없는 값(예: "캠핑용품", "1인 가구 살림")이 들어오면 그 값 자체를 핵심 키워드로 검색 쿼리 작성. 한국어 보편 표현으로 변형 허용 (예: "1인 가구 살림" → "혼자 사는 직장인 살림 트렌드").
````

---

## 1-3. 출력 스키마 sources 옆 주석 추가 (체인 흐름 명시)

### BEFORE

````
  "trending_topics": [
    {
      "topic": "주제 (한 줄, 25자 이내)",
      "why_trending": "왜 지금 뜨는지 (2-3문장, 구체적)",
      "sources": [
        {"domain": "naver.com", "url": "https://...", "date": "2026-05"}
      ],
      "estimated_volume": "high|medium|low",
      "longevity": "evergreen|seasonal|spike"
    }
  ],
````

### AFTER

````
  "trending_topics": [
    {
      "topic": "주제 (한 줄, 25자 이내)",
      "why_trending": "왜 지금 뜨는지 (2-3문장, 구체적)",
      "sources": [
        // 이 sources는 Strategy Planner → Writer → Fact-Checker로 흘러감. 완전성·정확성 필수.
        {"domain": "naver.com", "url": "https://...", "date": "2026-05"}
      ],
      "estimated_volume": "high|medium|low",
      "longevity": "evergreen|seasonal|spike"
    }
  ],
````

---

# 작업 2: backend/agents/prompts/02_audience_analyst.md

## 2-1. 입력 스키마에 오케스트레이터 전달 방식 명시

### BEFORE

````
## 입력
```json
{
  "category": "...",
  "trending_topics": [ ... ]
}
```
````

### AFTER

````
## 입력
```json
{
  "category": "...",
  "trending_topics": [ ... ]  // Trend Scout 출력의 trending_topics만 전달됨 (오케스트레이터가 추출). summary/search_queries_used는 본 에이전트에서 무시.
}
```
````

---

## 2-2. 출력 스키마 angle_suggestion 옆 주석 추가 (Strategy Planner 참조 명시)

### BEFORE

````
  "audience_evaluation": [
    {
      "topic": "Trend Scout의 topic 그대로",
      "fit_score": 8,
      "reasoning": "왜 이 점수인지 (타겟 페르소나 관점, 2-3문장)",
      "concerns": "우려사항 (없으면 빈 문자열)",
      "angle_suggestion": "이 주제로 가면 어떤 앵글이 좋을지 1문장"
    }
  ],
````

### AFTER

````
  "audience_evaluation": [
    {
      "topic": "Trend Scout의 topic 그대로",
      "fit_score": 8,
      "reasoning": "왜 이 점수인지 (타겟 페르소나 관점, 2-3문장)",
      "concerns": "우려사항 (없으면 빈 문자열)",
      "angle_suggestion": "이 주제로 가면 어떤 앵글이 좋을지 1문장 (Strategy Planner가 final_topic.angle 결정 시 우선 참고)"
    }
  ],
````

---

# 작업 3: backend/agents/prompts/03_strategy_planner.md

## 3-1. 의사결정 로직에 6번 항목 추가 (데드락 방지 + angle_suggestion 참조)

### BEFORE

````
## 의사결정 로직 (절대 준수)
1. `audience_analyst.verdict.top_choice_topic`을 기본 후보로 검토
2. 만약 그 주제의 `trend_scout.sources`가 빈약하면(2개 미만) 다른 주제 재검토
3. `trend_scout.longevity`가 `spike`인 주제는 피함 (evergreen/seasonal 우선)
4. Audience fit_score 7 미만 주제는 선택 안 함
5. 최종 1개 선택. 나머지 2개는 `rejected_topics`에 사유 명시.
````

### AFTER

````
## 의사결정 로직 (절대 준수)
1. `audience_analyst.verdict.top_choice_topic`을 기본 후보로 검토
2. 만약 그 주제의 `trend_scout.sources`가 빈약하면(2개 미만) 다른 주제 재검토
3. `trend_scout.longevity`가 `spike`인 주제는 피함 (evergreen/seasonal 우선)
4. Audience fit_score 7 미만 주제는 선택 안 함
5. **3개 모두 fit_score 7 미만인 경우**: 최고점 1개 선택 + `deliberation`에 "audience fit 미흡 경고" 명시
6. `final_topic.angle` 결정 시 `audience_analyst.audience_evaluation[i].angle_suggestion`을 우선 참고. 채택 시 `deliberation`에 명시, 안 채택 시 이유 명시.
7. 최종 1개 선택. 나머지 2개는 `rejected_topics`에 사유 명시.
````

---

## 3-2. 출력 스키마 final_topic에 category 추가

### BEFORE

````
  "final_topic": {
    "title": "콘텐츠 가제목 (실제 발행 가능한 수준, 25자 이내)",
    "angle": "이 주제를 어떤 각도로 풀어낼지 1문장",
    "target_persona": "주요 독자 1명 구체적 묘사 (예: '맞벌이 30대 부모, 주말 가족 식사 메뉴 고민')",
    "content_type_recommendation": "A|B|C",
    "type_reasoning": "왜 이 타입을 추천하는지 1-2문장 (Format Architect 참고용)",
    "estimated_read_time_min": 3,
````

### AFTER

````
  "final_topic": {
    "category": "<입력 category 그대로>",
    "title": "콘텐츠 가제목 (실제 발행 가능한 수준, 25자 이내)",
    "angle": "이 주제를 어떤 각도로 풀어낼지 1문장",
    "target_persona": "주요 독자 1명 구체적 묘사 (예: '맞벌이 30대 부모, 주말 가족 식사 메뉴 고민')",
    "content_type_recommendation": "A|B|C",
    "type_reasoning": "왜 이 타입을 추천하는지 1-2문장 (Format Architect 참고용)",
    "estimated_read_time_min": 3,  // 본문 글자수 기반 추정 (한글 500자/분 기준). Writer는 무시 가능, 어드민 표시용.
````

---

## 3-3. data_grounding 스키마 변경 (source_hint → source 객체화)

### BEFORE

````
    "data_grounding": [
      {
        "fact": "본문에 반드시 인용할 데이터/사실",
        "source_hint": "Trend Scout가 제공한 출처 (Writer가 Fact-Checker에 전달)"
      }
    ]
````

### AFTER

````
    "data_grounding": [
      {
        "fact": "본문에 반드시 인용할 데이터/사실",
        "source": {
          "domain": "naver.com",
          "url": "https://...",
          "date": "2026-05"
        }
      }
    ]
````

---

## 3-4. 규칙 섹션에 Trend Scout 출력 개수 방어 한 줄 추가

### BEFORE (규칙 섹션 첫 두 줄)

````
## 규칙
- `final_topic`은 정확히 1개
- `rejected_topics`는 **정확히 2개** (Trend Scout가 3개 줬으므로)
````

### AFTER

````
## 규칙
- `final_topic`은 정확히 1개
- `rejected_topics`는 **정확히 2개** (Trend Scout가 3개 줬으므로)
- **방어 규칙**: Trend Scout가 어떤 이유로 3개 미만(2개 또는 1개)을 줬다면, rejected_topics는 `(받은 개수 - 1)`개. deliberation에 "Trend Scout가 N개만 제공" 명시.
````

---

# 작업 4: backend/agents/prompts/09_html_builder.md

## 4-1. 사용 자원 섹션 보강 (파일 누락 시 대응)

### BEFORE

````
## 사용 자원 (반드시 참조)
- `docs/samples/plustab_structure.md`: 클래스 정의·HTML 구조 규칙
- `docs/samples/type_a_sample.html`: A타입 (이미지+글) 기본 마크업
- `docs/samples/type_b_sample.html`: B타입 (슬라이드+랜딩URL) 기본 마크업
````

### AFTER

````
## 사용 자원 (반드시 참조)
- `docs/samples/plustab_structure.md`: 클래스 정의·HTML 구조 규칙
- `docs/samples/type_a_sample.html`: A타입 (이미지+글) 기본 마크업
- `docs/samples/type_b_sample.html`: B타입 (슬라이드+랜딩URL) 기본 마크업

위 3개 파일은 Phase 1에서 작성된 docs/samples/ 산출물. 본 작업 시점에 존재해야 함. **존재하지 않거나 접근 불가하면 `warnings`에 "sample/structure 파일 누락" 기록 후, 일반적인 HTML5 시맨틱 마크업(section/article/figure 등)으로 작성**. 임의 클래스명은 발명하지 말고 BEM 형식의 보수적 명명 사용.
````

---

## 4-2. 출력 스키마 html 필드 모순 해소

### BEFORE

````
  "html": "<완성된 HTML 문자열 (escape된)>",
````

### AFTER

````
  "html": "<완성된 HTML 문자열. JSON 문자열로 escape되며 들여쓰기·줄바꿈은 \\n 형태로 보존 가능 (가독성용).>",
````

추가로 규칙 섹션의 다음 줄 수정:

### BEFORE

````
- `html` 출력은 한 줄 JSON 문자열로 escape. 들여쓰기는 포함되어도 OK.
````

### AFTER

````
- `html` 출력은 JSON 문자열로 escape. 들여쓰기·줄바꿈은 `\n` 형태로 보존 가능 (가독성용).
````

---

## 4-3. 규칙 섹션에 swiper 라이브러리 명시

규칙 섹션의 "B타입의 swiper-box는 swiper 초기화 JS 누락 금지" 줄을 다음으로 교체.

### BEFORE

````
- B타입의 swiper-box는 swiper 초기화 JS 누락 금지
````

### AFTER

````
- B타입의 swiper-box는 다음 라이브러리 필수:
  - swiper-bundle CDN: `https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.js`
  - swiper-bundle CSS: `https://cdn.jsdelivr.net/npm/swiper@11/swiper-bundle.min.css`
  - 초기화 코드 inline `<script>`로 포함 필수
  - plustab_structure.md에 표준 패턴 있으면 따르고, 없으면 기본 `new Swiper('.swiper', { ... })` 패턴 사용
````

---

## 4-4. 작업 절차에 실제 이미지 URL 처리 default 명시

### BEFORE (작업 절차 마지막 5번)

````
5. 출처 마커 `[출처: domain, YYYY-MM]`는 본문에 그대로 노출 (sup/footnote 처리 없음, default)
````

### AFTER

````
5. 출처 마커 `[출처: domain, YYYY-MM]`는 본문에 그대로 노출 (sup/footnote 처리 없음, default)
6. **이미지 URL 처리 (default)**:
   - 입력에 실제 이미지 URL이 없으면 `https://image.lguplus.com/static/{slug}.jpg` 형태의 placeholder URL 사용
   - alt 텍스트는 `layout_hints.image_descriptions`에서 가져옴
   - 실제 URL 주입은 추후 별도 단계(이미지 생성 에이전트 또는 어드민 수동 입력)에서 처리
````

---

# 작업 5: docs/NEXT_BUNDLE_NOTES.md §7 신규 섹션 추가

기존 파일 끝부분 (§6 다음)에 다음 내용을 append:

````
## 7. Step 2/3 작업 진입 전 결정·구현 필요 사항 (묶음 2 Step 1 검토에서 도출)

### 7-1. 외부 CDN URL config화 (Step 2 검토)
- mathjs (12.4.2), swiper (v11) 등 CDN URL이 prompt에 하드코딩됨
- 보안 패치·버전 업데이트 시 prompt 재편집 필요
- 옵션 A: 현행 유지 (단순)
- 옵션 B: `backend/config/cdn_urls.json` 분리 → base_agent가 prompt에 주입 → prompt는 키만 참조
- Step 2 base_agent 일반화 시 검토

### 7-2. 실제 이미지 URL 주입 시점 (Step 3 검토)
- HTML Builder는 입력에 실제 이미지 URL 없음
- 현재 default: placeholder URL `https://image.lguplus.com/static/{slug}.jpg` 사용
- 옵션 A: 사람이 어드민에서 채움 (default, MVP)
- 옵션 B: 별도 이미지 생성 에이전트가 layout_hints.image_descriptions로 생성 → 오케스트레이터가 final_content에 주입 → HTML Builder가 받음
- Step 3 오케스트레이터 설계 시 결정

### 7-3. 에이전트 간 데이터 흐름 명세 (Step 3 필수)
- 각 prompt의 입출력 스키마는 정의되었으나, 오케스트레이터가 어느 필드를 어느 에이전트에 어떻게 잘라서 넘기는지 명세 누락
- Step 3 Topic Newsroom / Content Newsroom 오케스트레이터 설계 시 명시 필요:
  - Trend Scout 출력의 어느 필드가 Audience Analyst 입력으로 가는지 (현재 `trending_topics`만)
  - Strategy Planner는 Trend Scout + Audience Analyst 출력을 어떻게 합쳐 받는지
  - Strategy Planner.final_topic이 Writer.strategy로 들어갈 때 매핑 (category는 외부에서 별도 주입 또는 final_topic.category에서 추출)
  - Editor.final_content + Format Architect 출력이 HTML Builder 입력으로 합쳐지는 방식
- 권장: `backend/orchestrators/data_flow_spec.md` 또는 오케스트레이터 코드 상단 주석으로 명세화
````

---

# 작업 6: PROGRESS.md 업데이트

## 6-1. 의사결정 로그에 2026-05-23 자 항목 추가

다음 항목 추가:

````
- 2026-05-23 묶음 2 Step 1 검토 패치 13건 적용 완료:
  - Trend Scout: target_date 활용 명시, category 자유 입력 처리, sources 체인 흐름 주석
  - Audience Analyst: 오케스트레이터 전달 방식 명시, angle_suggestion 참조 흐름 주석
  - Strategy Planner: 의사결정 로직 데드락 방지(rule 5) + angle_suggestion 참조(rule 6) 추가, final_topic.category 추가, data_grounding.source 객체화, Trend Scout 결과 개수 방어 규칙
  - HTML Builder: sample 파일 누락 시 대응, html escape 모순 해소, swiper 라이브러리 CDN 명시, 이미지 URL default 처리(placeholder URL)
- 2026-05-23 묶음 2 Step 2/3 진입 전 미정사항 3건 NEXT_BUNDLE_NOTES §7로 정리:
  - 7-1 외부 CDN URL config화 (Step 2 검토)
  - 7-2 실제 이미지 URL 주입 시점 (Step 3 검토)
  - 7-3 에이전트 간 데이터 흐름 명세 (Step 3 필수)
````

## 6-2. 진행률 변경 없음

- 묶음 2 Step 1 항목 4개는 이미 ✅ 처리됨
- 이번 패치는 품질 개선이므로 별도 체크리스트 항목 없음
- 현재 20/46 (43.5%) 유지

## 6-3. 마지막 업데이트 일자 2026-05-23 유지

---

# 실행 후 보고 항목

작업 완료 후 다음을 보고:

1. 4개 prompt 파일 패치 적용 확인 (파일별 변경 라인 수)
2. NEXT_BUNDLE_NOTES.md §7 추가 확인 (7-1, 7-2, 7-3)
3. PROGRESS.md 의사결정 로그 신규 항목 2건 확인
4. git status (스테이징은 하지 말 것)
5. 다음 단계: 묶음 2 Step 2 (base_agent.py 일반화) 진입 준비 완료 안내

---

# 주의사항

- **코드 실행이나 import 테스트 안 함**. 파일 편집만.
- 기존 prompt 파일의 다른 부분은 손대지 말 것.
- BEFORE/AFTER 블록의 들여쓰기 정확히 유지.
- JSON 코드블록 내부 주석(`//`) 형식 유지.
- 모든 파일 UTF-8 인코딩 유지.
- git stage는 사용자가 직접. 절대 자동 add/commit 금지.

# 묶음 1 패치 명령서

**작성일**: 2026-05-23  
**대상**: AIDEN Phase 2 묶음 1 (콘텐츠 품질 라인 5개)  
**범위**: 16건 prompt 패치 + NEXT_BUNDLE_NOTES.md 보강 + PROGRESS.md 업데이트  
**실행 방식**: 코드 실행/테스트 없이 파일 편집만

---

## 작업 개요

| 작업 | 파일 | 변경 건수 |
|---|---|---|
| 1 | `backend/prompts/06_devils_advocate.md` | 3건 |
| 2 | `backend/prompts/07_editor_in_chief.md` | 5건 |
| 3 | `backend/prompts/08_format_architect.md` | 2건 |
| 4 | `backend/prompts/04_writer.md` | 3건 |
| 5 | `backend/prompts/05_fact_checker.md` | 3건 |
| 6 | `docs/NEXT_BUNDLE_NOTES.md` | 5개 항목 추가 |
| 7 | `PROGRESS.md` | 의사결정 로그 + 이슈 업데이트 |

**총 16건 패치 + 메모 5건 추가 + 진행상황 갱신**

---

# 작업 1: backend/prompts/06_devils_advocate.md

## 1-1. 입력 스키마에 category 추가

### BEFORE

````
{
  "iteration": 1,                       // 1, 2, 3
  "annotated_draft": { ... },           // Fact-Checker 출력
````

### AFTER

````
{
  "iteration": 1,                       // 1, 2, 3
  "category": "맛집|AI트렌드|안전|문화|기타",
  "annotated_draft": { ... },           // Fact-Checker 출력
````

---

## 1-2. 출력 스키마 carried_over_from_previous 주석 보강

### BEFORE

````
  "carried_over_from_previous": [
    // iteration >= 2일 때만: previous_critiques 중 안 고쳐진 것 location 배열
  ]
````

### AFTER

````
  "carried_over_from_previous": [
    // iteration 1: 빈 배열 []
    // iteration 2+: previous_critiques 중 안 고쳐진 것의 location 문자열 배열
  ]
````

---

## 1-3. "절대 규칙" 섹션 끝에 두 줄 추가

### BEFORE (마지막 줄)

````
- `pass_threshold`: 위 표의 통과 기준 충족 시 true
````

### AFTER

````
- `pass_threshold`: 위 표의 통과 기준 충족 시 true
- **critical_issues 개수와 pass_threshold는 독립.** 라운드별 필수 비판 개수는 무조건 채우되, 점수 기준 충족 시 pass=true. 비판 있다고 자동 fail 아님.
- `category`는 tone_authenticity 점수 매길 때 카테고리별 톤 기준(맛집·문화="~다", 안전="~다+~하세요", AI트렌드="~죠/~어요")으로 평가
````

---

# 작업 2: backend/prompts/07_editor_in_chief.md

## 2-1. 의사결정 로직 표 아래 보강 문구 추가

의사결정 로직 표 끝난 직후, "추가 트리거" 섹션 바로 위에 한 줄 추가.

### BEFORE

````
| **3** | **false** | **`approved` (강제 종료)** + `final_content.known_weaknesses`에 남은 약점 명시 |

추가 트리거:
````

### AFTER

````
| **3** | **false** | **`approved` (강제 종료)** + `final_content.known_weaknesses`에 남은 약점 명시 |

**iter 3 강제 종료 시 `known_weaknesses` 필수 포함 항목**: DA의 잔여 critical_issues + Fact-Checker의 unverified/corrected claim + confidence_score ≤6 사유. 사실 결함은 절대 누락 금지.

추가 트리거:
````

---

## 2-2. 비판 수용 규칙 섹션 전체 교체

### BEFORE

````
## 비판 수용 규칙
- `critique.critical_issues` 중 **최소 60% 이상 수용** (`accepted_critiques`)
- 수용 안 한 건 `rejected_critiques`에 합리적 이유 명시 (1-2문장)
- "carried_over_from_previous"가 있으면 우선 수용 검토
````

### AFTER

````
## 비판 수용 규칙
- 라운드별 최소 수용 개수:
  - iter 1 (DA 5개) → 최소 3개 수용
  - iter 2 (DA 3개) → 최소 2개 수용
  - iter 3 (DA 1개) → 1개 수용 또는 명확한 reject 사유
- 수용 안 한 건 `rejected_critiques`에 합리적 이유 명시 (1-2문장)
- `carried_over_from_previous`에 있는 건 최우선 수용 검토
````

---

## 2-3. 출력 스키마 - accepted_critiques.issue 객체화 & rejected_critiques 동일 적용

### BEFORE

````
  "accepted_critiques": [
    {
      "issue": "DA 지적 원문",
      "action": "직접 수정함 | Writer에게 재작성 요청"
    }
  ],
  "rejected_critiques": [
    {
      "issue": "DA 지적 원문",
      "reason": "왜 안 받아들이는지 (1-2문장)"
    }
  ],
````

### AFTER

````
  "accepted_critiques": [
    {
      "issue": {"location": "DA가 지적한 위치", "problem": "DA가 지적한 문제"},
      "action": "직접 수정함 | Writer에게 재작성 요청"
    }
  ],
  "rejected_critiques": [
    {
      "issue": {"location": "...", "problem": "..."},
      "reason": "왜 안 받아들이는지 (1-2문장)"
    }
  ],
````

---

## 2-4. 출력 스키마 - revision_instructions 배열화 & final_content 기반 명시

### BEFORE

````
  // decision == "approved"일 때만:
  "final_content": {
````

### AFTER

````
  // decision == "approved"일 때만:
  // 기반: Fact-Checker의 annotated_draft (출처 inline 유지) + accepted_critiques 반영본
  "final_content": {
````

### BEFORE

````
  // decision == "needs_revision"일 때만:
  "revision_instructions": "Writer에게 줄 구체적 지시 (수정할 섹션·문장 단위로 명시, 3-7개 항목)"
}
````

### AFTER

````
  // decision == "needs_revision"일 때만:
  "revision_instructions": [
    {
      "target": "수정 대상 (예: 'section 2 첫 문장', 'closing 마지막 줄')",
      "instruction": "구체적 지시 (1-2문장)"
    }
    // 3-7개 항목
  ]
}
````

---

## 2-5. "규칙" 섹션의 editorial_decision 톤 가이드 강화

### BEFORE

````
- `editorial_decision`은 의식의 흐름 회의실 톤 OK. 단 결론은 명확히.
````

### AFTER

````
- `editorial_decision`: **결론 한 문장 + 근거 2-3문장** 구조. 추임새("음...", "그래서...") 금지. 회의실 톤은 OK하되 의식의 흐름 식 늘어뜨리기 금지.
````

---

# 작업 3: backend/prompts/08_format_architect.md

## 3-1. 출력 스키마에 base_layout 추가

### BEFORE

````
  "selected_type": "A | B | C",
  "type_reasoning": "왜 이 타입인지 (2-3문장)",
````

### AFTER

````
  "selected_type": "A | B | C",
  "base_layout": "A | B",  // C일 때만 의미: C의 base가 슬라이드 포함(B) 여부. A 선택 시 selected_type과 동일.
  "type_reasoning": "왜 이 타입인지 (2-3문장)",
````

---

## 3-2. "규칙" 섹션 끝에 카테고리 "기타" 처리 추가

### BEFORE (마지막 줄)

````
- 카테고리 "맛집"·"문화"는 A/B 기본, C는 비교 가치 있을 때만
````

### AFTER

````
- 카테고리 "맛집"·"문화"는 A/B 기본, C는 비교 가치 있을 때만
- 카테고리 "기타" 또는 매핑 없는 경우: 본문 성격 분석 후 A 기본, 슬라이드성·다단 소개면 B, 체험 가치 명확하면 C
````

---

# 작업 4: backend/prompts/04_writer.md

## 4-1. 입력 스키마의 editor_instructions 배열화 + 카테고리 일관성 명시

### BEFORE

````
  "editor_instructions": "..."          // Editor-in-Chief revision 지시
}
````

### AFTER

````
  "editor_instructions": [              // Editor-in-Chief revision 지시 (배열)
    {"target": "수정 대상", "instruction": "구체적 지시"}
  ]
}
````

**추가**: 입력 스키마 코드블록 바로 아래에 다음 한 줄 추가.

### BEFORE (입력 스키마 블록 다음 줄, 보통 빈 줄 또는 다음 섹션 헤더)

`## 출력 형식 (반드시 이 JSON 그대로)` 헤더 바로 앞에 다음 줄 삽입:

### AFTER (삽입할 내용)

````
**입력 비고**: iter 2+ 에서도 `category`는 최상위 필드로 동일하게 전달됨. `previous_draft.category`와 항상 일치.

````

---

## 4-2. 출력 스키마 보정 - category 주석화 + revision_notes 배열화

### BEFORE

````
  "draft_version": 1,
  "category": "",
````

### AFTER

````
  "draft_version": 1,
  "category": "<입력 category 그대로>",
````

### BEFORE

````
  "revision_notes": "iteration >= 2일 때만: editor_instructions의 어느 지시를 어떻게 반영했는지 항목별로"
}
````

### AFTER

````
  "revision_notes": [
    // iteration 1: 빈 배열 []
    // iteration 2+: editor_instructions 각 항목별 반영 결과
    {
      "target": "editor_instructions[N]의 target 그대로",
      "applied": "어떻게 반영했는지 1-2문장"
    }
  ]
}
````

---

## 4-3. "규칙" 섹션에 strategy 활용 가이드 추가

### BEFORE (규칙 섹션 첫 줄)

````
## 규칙
- 모든 수치·날짜·고유명사·인용은 `fact_claims`에 반드시 명시
````

### AFTER

````
## 규칙
- `strategy` 활용:
  - `key_messages`: 본문에 모두 반영 (필수)
  - `data_grounding`: 본문에 반드시 인용·반영 (필수)
  - `target_persona`: 톤·예시 선택 시 참고
  - `content_type_recommendation`: Format Architect 영역. Writer는 무시.
- 모든 수치·날짜·고유명사·인용은 `fact_claims`에 반드시 명시
````

---

# 작업 5: backend/prompts/05_fact_checker.md

## 5-1. annotated_draft.sections에 fact_claims 유지 + status 메타

### BEFORE

````
  "annotated_draft": {
    "title": "...",
    "subtitle": "...",
    "intro": "...",
    "sections": [
      {
        "heading": "...",
        "body": "본문 중 verified된 fact에 [출처: naver.com, 2025-04] 형식 삽입"
      }
    ],
    "closing": "...",
    "cta": "..."
  },
````

### AFTER

````
  "annotated_draft": {
    "title": "...",
    "subtitle": "...",
    "intro": "...",
    "sections": [
      {
        "heading": "...",
        "body": "본문 중 verified된 fact에 [출처: naver.com, 2025-04] 형식 삽입",
        "fact_claims": [
          {"claim": "Writer 원문 그대로", "status": "verified|corrected|unverified"}
        ]
      }
    ],
    "closing": "...",
    "cta": "..."
  },
````

---

## 5-2. 검증 절차에 [출처:] 삽입 위치 규칙 추가 (5번 항목 신설)

### BEFORE

````
4. 출처 URL과 발행일 기록
````

### AFTER

````
4. 출처 URL과 발행일 기록
5. `[출처: domain, YYYY-MM]` 마커 삽입 위치:
   - 해당 사실이 들어간 **문장 끝, 마침표 앞**
   - 한 문장에 출처 여러 개면 `[출처: A, 2025-04; B, 2025-03]` 형식으로 묶음
   - 단어 중간·문장 시작에 박지 말 것 (HTML Builder 정규식 매칭 깨짐)
````

---

## 5-3. confidence_score 계산식 차등화

### BEFORE

````
- `confidence_score`: 1-10 정수
  - 모든 claim이 verified → 9-10
  - corrected/unverified 1-2개 → 7-8
  - 3개 이상 문제 → 6 이하 (Editor가 재작성 트리거)
````

### AFTER

````
- `confidence_score`: 1-10 정수. 계산 방식 = 10 - (corrected 개수 × 1) - (unverified 개수 × 2)
  - 결과가 6 이하면 Editor가 재작성 트리거 (iter < 3일 때)
  - corrected는 Editor가 수정안으로 처리 가능 → 감점 1
  - unverified는 출처 없음 → 감점 2 (더 치명적)
  - 하한 1, 상한 10으로 clip
````

---

# 작업 6: docs/NEXT_BUNDLE_NOTES.md 보강

기존 파일 끝부분에 다음 섹션 5개를 추가. 기존 §1~§4 다음에 이어지도록 번호 조정 (현재 §1 HTML Builder ~ §4 진행률 추적이 있음. 그 뒤에 §5로 시작).

기존 마지막 항목 뒤에 다음 내용을 그대로 append:

````
## 5. Format Architect → HTML Builder 핸드오프 정의

### 5-1. placeholder_locations.location 형식
- 현재 dotted notation 사용 (예: "section.hero.img-figure")
- HTML Builder가 이걸 어떻게 해석할지(CSS selector? 가상 경로? AST?) 묶음 2에서 정의
- 권장: AIDEN 자체 mini-DSL 정의 후 HTML Builder가 파싱

### 5-2. layout_hints.image_descriptions 용도
- alt text용? 이미지 생성 프롬프트용? placeholder URL 캡션용?
- 묶음 2 HTML Builder 또는 이후 이미지 생성 에이전트에서 어떻게 소비할지 정의

### 5-3. placement: between_sections 모호성
- "어느 섹션 사이"인지 명시 필요
- 권장: between_section_N_and_N+1 형식 또는 LLM이 인덱스 명시

### 5-4. CALCULATOR.formula 안전성
- 문자열 수식 → JS eval 위험
- mathjs 같은 안전 표현식 파서 도입 또는 화이트리스트 연산자(+, -, *, /, 괄호)만 허용
- HTML Builder 또는 Frontend 렌더링 단계에서 처리

### 5-5. Google Search Grounding 호출 단위
- Fact-Checker가 claim 1개당 1회 호출인지, 묶어서 호출인지 결정 필요
- 비용·속도 트레이드오프
- Content Newsroom 오케스트레이터 또는 base_agent에서 분기 처리

## 6. base_agent 치환 화이트리스트 강제 (이슈/리스크에서 이관)

- `{{VAR}}` 치환은 Format Architect의 `placeholder_locations` 화이트리스트 기반
- 매핑 외 `{{VAR}}` 패턴은 무시 (= 주석 안에 있는 변수 자동 보호)
- type_a/b.html 헤더 주석의 문서화용 `{{VAR}}` 안전하게 보존됨
- 묶음 2 base_agent.py 구현 시 치환 함수에 명시
````

---

# 작업 7: PROGRESS.md 업데이트

## 7-1. 의사결정 로그에 다음 항목 추가 (날짜: 2026-05-23)

````
- 2026-05-23 묶음 1 검토 패치 16건 적용 완료:
  - DA: 입력에 category 추가, critical_issues 개수와 pass_threshold 독립 명시, carried_over iter 1=[] 명시
  - Editor: 비판 수용 규칙 라운드별 차등(3/2/1), accepted/rejected_critiques.issue 객체화, revision_instructions 배열화, final_content 기반은 annotated_draft, editorial_decision 톤 강화, iter 3 강제 종료 시 known_weaknesses 필수 포함 항목 명시
  - Format Architect: base_layout 필드 추가, 카테고리 "기타" 처리 규칙
  - Writer: editor_instructions/revision_notes 배열화, strategy 활용 가이드, iter 2+ category 일관성
  - Fact-Checker: annotated_draft에 fact_claims 유지+status 메타, [출처:] 삽입 위치 규칙, confidence_score 계산식 차등(corrected -1 / unverified -2)
- 2026-05-23 base_agent 치환 화이트리스트 강제 결정 (옵션 B): placeholder_locations 매핑 외 {{VAR}}는 무시 → 주석 자동 보호. 마커 통일 유지.
````

## 7-2. 이슈/리스크 항목 업데이트

### BEFORE 항목

````
HTML Builder placeholder 주석 내부 치환 위험 (중간) — ...
````

### AFTER

해당 항목을 다음으로 대체:

````
HTML Builder placeholder 주석 내부 치환 위험 (해결책 확정) — base_agent 치환을 Format Architect의 placeholder_locations 화이트리스트 기반으로 구현하기로 결정. 매핑 외 {{VAR}}는 무시. 묶음 2 base_agent.py 구현 시 적용. 상세는 docs/NEXT_BUNDLE_NOTES.md §6.
````

## 7-3. 진행률 변경 없음

- 묶음 1 작업 항목 5개는 이미 ✅ 처리됨
- 이번 패치는 품질 개선이므로 별도 체크리스트 항목 없음
- 현재 16/46 (34.8%) 유지

---

# 실행 후 보고 항목

작업 완료 후 다음을 보고:

1. 5개 prompt 파일 패치 적용 확인 (파일별 변경 라인 수)
2. NEXT_BUNDLE_NOTES.md §5, §6 추가 확인
3. PROGRESS.md 의사결정 로그 / 이슈 갱신 확인
4. 변경 사항이 git status에 어떻게 잡히는지 (스테이징은 하지 말 것, 사용자가 직접 커밋)
5. 다음 단계: 묶음 2 진입 준비 완료 안내

---

# 주의사항

- **코드 실행이나 import 테스트 안 함**. 파일 편집만.
- 기존 prompt 파일의 다른 부분(페르소나, 컨텍스트 등)은 손대지 말 것.
- BEFORE/AFTER 블록의 들여쓰기 정확히 유지.
- JSON 코드블록 내부 주석(`//`) 형식 유지.
- 모든 파일 UTF-8 인코딩 유지.

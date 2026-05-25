# 묶음 3 Step 1: 재현성 E2E 검증 (3회 실행)

- **ID**: B3-S1
- **우선순위**: 묶음 3 우선순위 2 (재현성 검증) — P2 R3 효과 검증 겸용
- **목적**:
  1. P2 R3 패치 효과 검증 (FC iter3 `verification_log` 누락 해소 확인)
  2. 카테고리 간 재현성 확인 (맛집 외 도메인에서도 정상 작동하는가)
- **선결 조건**: P2 R3 패치 적용 완료 (`prompts/05_fact_checker.md` 변경됨)

---

## 실행 항목

### E2E 3회 실행

| Run | 카테고리 | 주제 시드 | 목적 |
|---|---|---|---|
| 1 | 맛집 | "가족 식비 절약" (run 1 재현) | P2 R3 패치 직접 검증 — 동일 시나리오에서 `verification_log` 누락 해소되는지 1:1 비교 |
| 2 | 안전 | 자유 (Trend Scout 토픽 선정) | 도메인 차이 재현성 확인 (수치·통계 중심) |
| 3 | AI트렌드 | 자유 (Trend Scout 토픽 선정) | 도메인 차이 재현성 확인 (트렌드·예측 중심) |

### Run 1 (맛집 재현) 세부 지침
- 기존 시나리오와 동일한 strategy로 시작 시도. 가능한 방법:
  - **방법 A**: `traces/<이전_session>/03_strategy_planner.json` 의 output을 strategy fixture로 주입
  - **방법 B**: Trend Scout부터 새로 돌리되 카테고리 preset만 "맛집"으로 고정
  - 둘 다 환경상 어려우면 방법 B로 진행하고 보고에 명시
- 목표는 strategy 재현이 아니라 **FC iter3 동작 검증**이므로 strategy가 약간 달라도 무방

### Run 2, 3 (안전·AI트렌드) 세부 지침
- 카테고리 preset만 지정. 주제는 Trend Scout 자유 선정
- 각 회차 새 session

---

## 검증 체크리스트 (회차별 평가)

각 run의 `traces/<session>/05_fact_checker_iter3.json` 에 대해 아래 4항목 평가.

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| C1 | verification_log 길이 | `sum(len(s.fact_claims) for s in input.sections)` 와 일치 |
| C2 | entry 필드 완전성 | 각 verification_log entry에 evidence·source_url·source_date 모두 채워짐 |
| C3 | 거울 일치 | `annotated_draft.sections[].fact_claims[].status` 가 `verification_log[i].status` 와 일치 |
| C4 | 빈 케이스 처리 | 빈 fact_claims인 경우 confidence_score==1 + summary에 경고 문구 포함 (자연 발생 시에만 평가) |

### 회차별 통과 기준
- C1·C2·C3 모두 OK → **PASS**
- C4는 빈 fact_claims 자연 발생 시에만 평가, 발생 안 하면 N/A 처리

### 전체 통과 기준
- 3회 중 **3회 모두 PASS** → P2 R3 패치 확정
- 3회 중 **2회 PASS, 1회 FAIL** → 실패 회차 원인 분석 후 추가 1회 재시도
- 3회 중 **2회 이상 FAIL** → P2 R3 패치 롤백 후 재진단

---

## 부수 관찰 항목 (PASS/FAIL 판정과 무관, 보고용)

- 각 회차의 **수렴 iter 수** (FC가 iter 몇에서 confidence_score≥7 도달했는가)
- 각 회차의 **총 LLM 호출 수 / duration**
- 각 회차의 **Devil's Advocate 평균 점수**
- 카테고리별 fact_claims 평균 개수 (도메인 차이 관찰)

---

## 실행 환경

- LLM: gemini-2.5-flash (google-genai 2.6.0)
- Grounding: `types.Tool(google_search=types.GoogleSearch())` 활성
- 예상 비용: $0.02 × 3 ≈ $0.06
- 예상 시간: 30~45분

---

## 실행 후 보고 항목

다음을 순서대로 보고:

### 1. 회차별 요약 (테이블)
| Run | 카테고리 | session_id | 수렴 iter | C1 | C2 | C3 | C4 | 종합 |
|---|---|---|---|---|---|---|---|---|

### 2. 회차별 final_output.html 절대 경로
- Run 1: `/path/to/...`
- Run 2: `/path/to/...`
- Run 3: `/path/to/...`

### 3. P2 R3 패치 판정
- 전체 통과 기준 적용 결과 (PASS/FAIL/재시도 필요)
- FAIL 시 실패 회차의 `verification_log` 누락 패턴 분석 (어떤 entry가 비었는지, status는 어땠는지)

### 4. 부수 관찰 결과
- 카테고리별 수렴 iter 평균
- 카테고리별 fact_claims 평균 개수
- 빈 fact_claims 자연 발생 여부 (어느 회차/섹션)

### 5. 비용/시간 실측
- 총 호출 수, 총 duration, 총 토큰 (가능 시)

### 6. 이상 징후 (있는 경우만)
- JSON 파싱 실패, 정규식 매칭 실패, 출처 마커 위치 오류 등 P2 R3 외 발견 사항

---

## 제약 사항

- git add / commit / stage **금지** (사용자가 직접 수행)
- 명세서에 없는 prompt 파일·코드 수정 **금지**
- LLM 호출 실패 시 재시도 1회까지만 (무한 재시도 금지)
- 회차 간 캐시 공유 금지 (각 회차 독립 session)

---

## 빈 fact_claims 케이스 (#W-fc-empty)

본 회차에서는 **자연 발생만 관찰**. 강제 재현은 별도 이슈로 남김.
3회 중 자연 발생하면 C4 평가, 안 하면 N/A.

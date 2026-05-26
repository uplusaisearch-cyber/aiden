# 묶음 3 Step 2 E2E: Judge Panel 포함 실제 LLM E2E 검증

- **ID**: B3-S2-E2E
- **우선순위**: 묶음 3 우선순위 3 (Judge Panel) 의 검증 단계
- **목적**:
  1. B3-S2 패치 (Judge Panel 백엔드) 가 실제 LLM 호출 환경에서 정상 작동하는지 검증
  2. 3-Model (Gemini + GPT + Claude) 호출이 동시·정상 응답하는지 확인
  3. 모델 우선순위 (UI override > env > config) 실측 검증
  4. 어드민 UI (B3-S3) 진입 전 Judge 데이터 모양 최종 확정 + mock 데이터 확보
- **선결 조건**: B3-S2 commit 완료, `.env`에 OPENAI_API_KEY + ANTHROPIC_API_KEY 설정

---

## 실행 항목

### E2E 3회 실행

| Run | 카테고리 | 주제 시드 | 목적 |
|---|---|---|---|
| 1 | 맛집 | Trend Scout 자유 | 기본 동작 검증 |
| 2 | 안전 | Trend Scout 자유 | 카테고리 다양성 (수치·통계 중심) |
| 3 | AI트렌드 | Trend Scout 자유 | 카테고리 다양성 (트렌드 중심) |

### 모델 우선순위 추가 검증 (Step 5)
- Run 4 (선택): `JUDGE_GEMINI_MODEL=gemini-2.5-flash` 환경변수 설정 후 1회 실행
  - `models_resolution_source.gemini == "env"` 인지 확인
  - 다른 두 모델은 여전히 "config" 인지 확인
  - **이 회차는 카테고리 무관, 환경변수 동작 검증만 목적**

---

## 검증 체크리스트

각 run의 `runs/<session>/judge_panel.json` 에 대해 평가.

### A. 기본 동작 (Run 1·2·3 모두 평가)

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| A1 | judge_panel.json 파일 생성 | 파일 존재 + JSON 파싱 가능 |
| A2 | status | `"completed"` (3 모델 모두 성공) |
| A3 | 3 모델 evaluations 모두 존재 | `gemini`, `gpt`, `claude` 키 모두 채워짐 |
| A4 | 각 모델의 5 차원 점수 | `topic_fit`, `content_quality`, `interactivity`, `tone_authenticity`, `timeliness_trust` 모두 1~10 정수 |
| A5 | 각 모델의 5 차원 코멘트 | 동일 키 모두 채워짐, 빈 문자열 아님 |
| A6 | overall_score | 1~10 범위 숫자 (float OK) |
| A7 | strengths / weaknesses | 각 배열 길이 ≥ 1 |
| A8 | one_line_verdict | 비어있지 않음, 50자 이내 권장 (초과 시 경고만, FAIL 아님) |

### B. Aggregate 계산 정확성 (Run 1·2·3 모두 평가)

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| B1 | mean_scores 계산 | 3 모델 점수의 산술 평균 일치 (소수 둘째자리 허용) |
| B2 | stdev_scores 계산 | 표본표준편차 (n-1 또는 n=3 단순 σ) 명세서 구현 일치 |
| B3 | weighted_total | mean_scores × 가중치 합 = weighted_total (소수 둘째자리 허용) |
| B4 | outliers 감지 | σ≥0.5 AND \|delta\|≥1.0 룰 적용 결과 일치 |
| B5 | failed_models | 빈 배열 (모두 성공한 경우) |
| B6 | duration_ms | > 0 |
| B7 | cost_usd_estimate | > 0 |

### C. 동시 호출 검증 (Run 1·2·3 모두 평가)

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| C1 | duration_ms | 단일 모델 호출 시간의 1.5배 이하 (동시 호출 효과 확인) |
| C2 | trace 로그 timestamp | 3 모델 호출 시작 시간이 거의 동시 (1초 이내 차이) |

### D. 모델 우선순위 (Run 4 선택, Run 1·2·3 부분 평가)

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| D1 | models_used 필드 존재 | 3 모델 이름 모두 기록 |
| D2 | models_resolution_source 필드 존재 | 3 모델 각각 `"config" / "env" / "runtime_override"` 중 하나 |
| D3 | Run 1·2·3 (env 미설정) | 모두 `"config"` |
| D4 | Run 4 (env 설정) | gemini="env", gpt="config", claude="config" |

### E. FullPipeline 통합 (Run 1·2·3 모두 평가)

| # | 체크 항목 | 통과 기준 |
|---|---|---|
| E1 | Stage 1·2·3 정상 산출 (회귀) | final_output.html 존재, 9 에이전트 trace 모두 정상 |
| E2 | Stage 4 trace 기록 | judge_panel trace highlight (3 모델 평균·표준편차·outlier) 정상 |
| E3 | metadata.json 에 judge 결과 병합 | weighted_total, outliers, status 등 핵심 필드 포함 |

### 회차별 통과 기준
- A·B·C·E 모두 OK → **PASS**
- D는 Run 1·2·3에서 D1·D2·D3 평가, Run 4 실행 시 D4 평가
- 1건이라도 FAIL → 종합 FAIL

### 전체 통과 기준
- Run 1·2·3 모두 PASS → B3-S2 패치 확정
- 2/3 PASS + 1 FAIL → 실패 원인 분석, 추가 1회 재시도
- 2 이상 FAIL → B3-S2 코드 재검토

---

## 부수 관찰 (PASS/FAIL 무관, 보고용)

### 모델 평가 패턴
- 각 모델별 5 차원 평균 점수 (어느 모델이 후한지, 짠지)
- one_line_verdict 샘플 (실제 어떤 톤·길이로 나오는지)
- strengths / weaknesses 분포 (어느 모델이 약점 더 많이 잡는지)
- outlier 자연 발생 여부 (몇 회 / 어느 차원)

### 비용·시간
- 회차당 Judge Panel 비용 (cost_usd_estimate) 실측
- 회차당 Judge Panel duration (전체 FullPipeline 중 Stage 4 비중)
- 단일 모델 평균 응답 시간

### 9 에이전트 단계 회귀 (B3-S1 결과와 비교)
- 수렴 iter (B3-S1: 평균 2.33 vs 본 회차)
- fact_claims 평균 개수
- Devil's Advocate 평균 점수

---

## 실행 환경

- LLM: 
  - Gemini: `gemini-2.5-pro` (Judge용) + `gemini-2.5-flash` (9 에이전트용)
  - GPT: `gpt-5` (config 기본값)
  - Claude: `claude-opus-4-7` (config 기본값)
- API 키: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- 예상 비용 (회차당):
  - 9 에이전트 ~$0.02 (B3-S1 실측)
  - Judge Panel ~$0.03 (명세서 추정)
  - 합계 ~$0.05 × 3회 = ~$0.15
- 예상 시간: 회차당 6~10분 (Judge 추가로 +2분 예상) × 3회 = 30~45분

---

## 실행 후 보고 항목

다음 순서대로 보고:

### 1. 회차별 요약 (테이블)

| Run | 카테고리 | session_id | A(8) | B(7) | C(2) | D | E(3) | 종합 |
|---|---|---|---|---|---|---|---|---|

- A·B·C·E는 항목 수 (예: A8/8 모두 통과 → A=OK)
- D는 Run별 평가 (Run 4 있으면 D4까지)

### 2. final_output.html + judge_panel.json 절대 경로
- Run 1: `final_output.html` / `judge_panel.json`
- Run 2: 같음
- Run 3: 같음
- (Run 4 있으면 추가)

### 3. B3-S2 패치 판정
- PASS / FAIL / 재시도 필요
- FAIL 시 어느 체크에서 실패했는지 + 원인 분석

### 4. 모델 평가 패턴 관찰
- 모델별 5 차원 평균 점수 테이블
- one_line_verdict 9개 (3 모델 × 3 회차) 샘플 전체 인용
- outlier 자연 발생 빈도

### 5. 비용·시간 실측
- 회차당 비용 (Judge + 9 에이전트 분리)
- 회차당 duration (Stage 4 비중)
- 총 비용 / 총 시간

### 6. 9 에이전트 회귀 비교 (vs B3-S1)
- 수렴 iter 평균
- fact_claims 평균
- Devil's Advocate 점수 추이

### 7. 이상 징후 (있는 경우만)
- LLM 호출 실패·재시도
- JSON 파싱 실패
- 비용 예산 초과
- B3-S2 외 발견 사항

---

## 제약 사항

- git add / commit / stage **금지** (사용자 직접)
- 명세서에 없는 prompt 파일·코드 수정 **금지**
- LLM 호출 실패 시 재시도 1회까지만
- 회차 간 캐시 공유 금지 (각 회차 독립 session)
- 비용 예산: 총 $0.30 초과 시 즉시 중단

---

## 후속 작업

본 명세서 PASS 완료 후 → **B3-S3-A** (Next.js 셋업 + 메인 페이지) 명세서 작성 진입.

본 회차 산출 데이터 (`judge_panel.json` 3~4개) 는 어드민 UI 개발 시 **mock 데이터로 활용**. 별도 백업 필요:
- `runs/<session>/judge_panel.json` 3개를 `docs/samples/judge_panel_samples/` 폴더로 복사
- 어드민 UI 개발 중 LLM 호출 없이 시각화 검증 가능

---

## 별도 이슈

- **#judge-cost-realdata**: GPT-5, Claude Opus 4.7 단가는 명세서 작성 시점 추정. 본 E2E 실측으로 cost_tracker 단가 테이블 갱신 검토
- **#judge-prompt-tuning**: 본 회차 결과의 모델별 평가 패턴 (어느 모델이 후한지) 관찰 → 필요 시 prompt 조정. 마감 후 검토

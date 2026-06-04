# Open Issues (AIDEN)

마감 6/9 전 처리 여부 결정 또는 마감 후 처리할 누적 이슈 목록.

**작성일**: 2026-05-25
**기준 시점**: 묶음 3 Step 1 (재현성 E2E) 완료 직후

---

## #W-fc-empty — writer가 fact_claims를 빈 배열로 만드는 케이스

- **발견**: 묶음 2 E2E run 2 (편의점 디저트 TOP5)
- **현상**: editor가 "트렌드 문구 삭제" 지시 → writer iter3가 본문 수치·고유명사 제거하며 fact_claims도 모두 `[]`로 만듦
- **위험도**: 중. P2 R3로 FC가 confidence_score=1 부여하도록 막아둠. 다만 iter3까지 갔는데 결국 final 진입은 가능
- **재현성**: 묶음 3 Step 1 (3회 E2E) 에서 자연 재현 0회. 강제 재현 안 함
- **처리 방향 후보**:
  - A. writer.md에 "본문에 검증 가능한 사실 N개 이상 포함" 강제 (감각 묘사 카테고리에선 부자연)
  - B. 카테고리별 정책 분리 (맛집·안전·AI트렌드는 강제, 디저트 리뷰 같은 감각 콘텐츠는 면제)
  - C. 현재 P2 R3 가드만으로 충분하다고 보고 close
- **우선순위**: 마감 후 검토. 현재 P2 R3 가드로 격리됨.

---

## #docs-path-mismatch — 명세서와 실제 레포 경로 불일치

- **발견**: 묶음 3 Step 1 실행 보고
- **현상**:
  - 명세서: `prompts/05_fact_checker.md`, `traces/<session>/`
  - 실제: `backend/agents/prompts/05_fact_checker.md`, `runs/<session>/agents/`
- **위험도**: 낮음. Claude Code가 실제 경로 기준으로 해석해 진행. 다만 매번 경로 보정 비용 발생
- **처리**:
  - 다음 명세서부터 실제 레포 경로 사용
  - 기존 명세서 (P2 R3, B3-S1) 는 재작성 안 함 (이미 실행 완료)
- **우선순위**: P0 (즉시 적용 — 다음 명세서 작성 시점부터)

---

## #windows-tmp-path — Claude Code 임시 파일 Windows 경로 비호환

- **발견**: 묶음 3 Step 1 실행 중
- **현상**: Claude Code가 보고용 임시 파일을 `/tmp/run_titles.txt` 로 쓰려다 `FileNotFoundError`. Windows에는 `/tmp` 없음
- **위험도**: 낮음. 본 파이프라인 결과에 영향 없음. Claude Code 부수 작업만 실패
- **처리 방향 후보**:
  - A. Claude Code 실행 시 시스템 프롬프트에 "Windows path 사용" 추가
  - B. Claude Code가 `tempfile.gettempdir()` 또는 `os.environ['TEMP']` 쓰도록 지시
- **우선순위**: 마감 후. 영향 없음.

---

## #da-iter3-regression — Devil's Advocate 점수 iter2→iter3 하락

- **발견**: 묶음 3 Step 1 Run 1 (맛집)
- **현상**: Devil's Advocate 점수 추이 3.6 → 6.2 → **5.8**. iter3 재작성이 개선되지 않고 오히려 점수 하락
- **가능한 원인**:
  - Editor 지시 품질 (모호하거나 상충하는 지시)
  - Writer가 editor 지시 반영하면서 다른 영역 품질 떨어뜨림
  - DA의 평가 기준이 iter마다 가변 (자가 일관성 문제)
- **위험도**: 중. 토론 시스템의 핵심 가정 (iteration → 품질 향상) 이 깨질 수 있음
- **추가 관찰 필요**:
  - 다른 카테고리에서도 재발하는지 (안전·AI트렌드는 iter2 수렴으로 평가 불가)
  - 묶음 3 우선순위 2 추가 E2E 시 데이터 더 모이면 패턴 확인
- **처리 방향 후보**:
  - A. DA 프롬프트에 "이전 iter 점수 대비 일관성 유지" 명시
  - B. iter3에서 점수 하락 시 iter2 결과 채택하는 백트래킹 로직
  - C. 현상 추적만 하고 마감 후 검토
- **우선순위**: 마감 전 1회 추가 데이터 수집 필요. 즉시 패치는 보류.

---

## #judge-env-key-mismatch — Settings 와 GeminiClient 의 API 키 환경변수 이름 불일치

- **발견**: B3-S2-E2E 실행 시점 (2026-05-26)
- **현상**: `backend/core/settings.py` 의 `gemini_api_key` 필드는 `GEMINI_API_KEY` 환경변수를 읽지만, 기존 `GeminiClient` 는 `GOOGLE_AI_STUDIO_API_KEY` 를 직접 읽음. 두 키 이름이 불일치해 JudgePanel `from_settings()` 초기화 단계에서 ValidationError 발생
- **우회**: `.env` 에 같은 값을 두 키로 중복 등록하여 임시 해결
- **처리 방향 후보**:
  - A. `settings.py` 가 두 키 모두 허용하도록 alias 추가
  - B. `GeminiClient` + `Settings` 의 키 이름을 한쪽으로 통일
- **우선순위**: 마감 후

---

## #judge-cost-realdata — judge_panel.cost_usd_estimate 단가표·토큰 추정 보정 필요

- **발견**: B3-S2-E2E Run 1·2·3 (2026-05-26)
- **현상**: `judge_panel.cost_usd_estimate` 가 명세서 추정 ($0.032/run) 의 약 4배 ($0.1375/run). 원인은 `_TOKEN_ESTIMATE = {input: 2000, output: 1000}` 가정 + Claude Opus 4.7 단가 ($15/$75 per 1M) 가 명세서 표와 차이가 있어서. 실제 청구액과의 격차 가능성
- **처리 방향**: 실제 billing 데이터로 `_JUDGE_PRICE_TABLE` 단가 테이블 + `_TOKEN_ESTIMATE` 토큰 추정치 보정. 본 회차 4회 실 청구액이 확인되면 그 값으로 갱신
- **우선순위**: 마감 후

---

## #judge-prompt-tuning — Gemini Judge 의 자기 모델 편향 의심

- **발견**: B3-S2-E2E Run 3 (2026-05-26)
- **현상**: Gemini Judge 가 자기 모델(Gemini-2.5-flash) 로 생성된 콘텐츠의 `timeliness_trust` 차원에서 9점 부여 (mean 6.33, delta +2.67, 본 회차 유일한 high outlier). GPT/Claude 는 5점
- **추가 관찰 필요**: 1회 outlier 라 단정 어려움. 추가 E2E 또는 어드민 UI 시연 중 패턴 관찰
- **처리 방향 후보**:
  - A. judge prompt 에 "자기 모델 평가 시 추가 엄격성" 명시 강화
  - B. Judge Gemini 만 입력 콘텐츠에서 생성 모델 ID 익명화 (입력 메타데이터 제거)
- **우선순위**: 마감 후

---

## #interactivity-structural-gap — interactivity 차원 점수 구조적으로 낮음

- **발견**: B3-S2-E2E Run 1·2·3 (2026-05-26)
- **현상**: `interactivity` 차원 점수가 3 모델 모두 일관되게 매우 낮음 (1~3점). 9 에이전트 파이프라인이 산출하는 콘텐츠의 인터랙티브 요소 자체가 약함
- **가능한 원인**: Format Architect / Game-ifier 단계에서 5종 인터랙티브 템플릿이 충분히 활용 안 됨
- **처리 방향 후보**:
  - A. Format Architect prompt 강화 — 인터랙티브 요소 의무화·다양화
  - B. 어드민 UI 에 "인터랙티브 강조" 옵션 추가하여 시연 시 활성화
- **우선순위**: 마감 후 (시연 자체에는 영향 없음)

---

## ✅ [closed] #W-recent-runs-crash — RecentRuns 컴포넌트 statusVariant default 누락 크래시

- **발견**: 2026-05-28 (B3-S3-C 직후 사용자 보고)
- **현상**: 메인 페이지 `/` 진입 시 `recent-runs.tsx:74` 에서 `Cannot read properties of undefined (reading 'color')` 크래시
- **진짜 원인 (사후 분석)**:
  1. 백엔드 `/api/runs` 가 `status: "failed_stage_1"` (그리고 잠재적으로 `"unknown"`) 같은 값을 반환할 수 있음. `RunStatus` union (`completed/partial/failed/running`) 에 없는 값
  2. `statusVariant()` switch 가 default 케이스 없음 → 미매칭 시 `undefined` 반환 → 74번 라인 `sv.color` 접근 시 크래시
  3. `toMockShape` 의 `as MockRecentRun["status"]` 캐스트가 타입 검사를 우회해 런타임에 도달
- **B3-S3-C 와의 관계**: **무관 (잠재 버그)**. B3-S3-C 는 `recent-runs.tsx` / `RunSummary` 경로를 건드리지 않았음. B3-S3-C 작업 후 사용자가 메인 페이지를 다시 열었을 때 `failed_stage_1` 데이터를 처음 마주쳐 표면화됨. 명세 §16 의 "회귀 없음" 결론은 ChatMessage 직렬화 변경에 한해 정확. 다만 회귀 점검 범위를 "메인 페이지가 크래시하지 않는지" 까지 넓혀서 확인했어야 했다는 점은 사후 반성 포인트
- **수정**: `statusVariant` 시그니처를 `string` 으로 완화 + `failed*` prefix 매칭 + 알 수 없는 상태는 회색 폴백. 함께 발견된 `CATEGORY_LABEL_MAP[run.category]` undefined (API 가 영문 id 가 아닌 한국어 라벨 반환) 도 `?? run.category` 폴백 적용. `npm run build` 통과
- **잔여**: 백엔드가 어떤 카테고리 라벨 / 상태값을 정식으로 노출할지 스펙 정리 필요 → `#api-category-label-mismatch` 로 분리

---

## #api-category-label-mismatch — /api/runs 가 영문 id 가 아닌 한국어 라벨로 category 반환

- **발견**: 2026-05-28 (#W-recent-runs-crash 분석 중 부수 발견)
- **현상**: `RunListResponse.runs[].category` 가 `"맛집" / "AI트렌드"` 같은 한국어 라벨로 옴. 프론트 `CategoryId` 는 `"food" / "ai-trend" / ...` 영문 id 라 `CATEGORY_LABEL_MAP[run.category]` 가 `undefined` → 현재는 폴백으로 raw 라벨 표시
- **위험도**: 낮음. 다만 카테고리 필터·아이콘·통계 동작 모두 영향 가능
- **원인 후보**: `run_manager.py` 의 `CATEGORY_LABEL` 매핑이 metadata 저장 시 라벨로 변환했고, `/api/runs` 가 그 라벨을 그대로 반환
- **처리 방향**:
  - A. `/api/runs` 응답 직전 라벨 → id 역매핑
  - B. metadata 저장 시 raw id 도 함께 저장하고 API 가 id 를 우선 반환
- **우선순위**: 마감 후 (B3-S3-D/E 와 함께 정리)

---

## ✅ [closed] #W-hydration-font-mismatch — layout.tsx 인라인 <style> hydration mismatch

- **발견**: 2026-05-28 (#W-recent-runs-crash 수정 직후, 메인 페이지 CSS 깨짐으로 사용자 보고)
- **현상**: 콘솔에 `Warning: Text content did not match. Server: ":root { --font-pretendard: &quot;...&quot;... }" Client: ":root { --font-pretendard: \"...\"... }"` → `Uncaught Error: Text content does not match server-rendered HTML` → 루트 전체가 client rendering 으로 fallback 되며 일부 스타일이 잠시 깨져 보임
- **원인**: `frontend/app/layout.tsx <head>` 안의 `<style>{`:root { --font-pretendard: "Pretendard Variable", ... }`}</style>` 인라인 스타일. React SSR 이 children-as-text 로 직렬화할 때 큰따옴표를 `&quot;` HTML 엔티티로 인코딩 → 클라이언트는 원본 따옴표로 재구성 → hydration 비교 mismatch
- **B3-S3-C 와의 관계**: **무관**. layout.tsx 인라인 style 은 B3-S3-A (Next.js 셋업) 시점부터 존재. #W-recent-runs-crash 를 고치자 그 위에 가려져 있던 CSS 깨짐이 표면화됨
- **수정 방향 선택**: 옵션 (A) — `--font-pretendard` CSS 변수를 `frontend/app/globals.css` 의 `:root` 블록으로 이전. CSS 파일 안에서는 따옴표가 그대로 보존되므로 mismatch 없음. layout.tsx 인라인 `<style>` 자체를 제거, `<link>` Pretendard CDN 로딩은 유지. Tailwind config 의 `fontFamily.korean: ["var(--font-pretendard)", ...]` 가 동일하게 작동
- **검증**: `npm run build` 6/6 페이지 정적 생성 PASS, 타입 에러 0. 사용자는 dev 서버 재시작 + 필요시 `.next/` 캐시 삭제 권장 (hydration 워닝이 캐시된 경우)
- **잔여**: 향후 `<head>` 에 동적 `<style>` 주입할 일이 있다면 `dangerouslySetInnerHTML={{__html: ...}}` 패턴 사용 + 가능하면 따옴표 escape 안전 처리

---

## ✅ [closed] #W-trace-viewer-history-missing — 완료된 run 진입 시 connecting 무한 대기

- **발견**: 2026-05-28 (B3-S3-C 직후 사용자 보고)
- **현상**: `/run/<id>` 페이지가 완료된 과거 run 으로 진입 시 ChatStream 의 "연결 중… 첫 메시지를 기다립니다" 안내가 영원히 표시되며 채팅·StagePanel 정보가 비어 있음. 라이브 run 만 정상 동작
- **원인**: 명세 B3-S3-C §6-1 의 `useRunStream` 훅이 SSE (`/api/stream/{id}`) 만 구독. 완료된 run 은 SSEBroker 에 새 publish 가 없으므로 EventSource 가 무기한 idle. 백엔드에는 이미 `GET /api/runs/{id}` 가 디스크 trace 를 ChatMessage 배열로 변환해 반환하지만 훅이 호출하지 않음
- **수정**: fetch-then-stream 패턴으로 `useRunStream` 재작성
  1. 마운트 시 `fetchRunDetail(runId)` 로 disk-recorded 메시지 일괄 로드 → `messages`, `currentAgent/Stage/Iter`, `startedAt`, `duration_sec` → `elapsedMs` 채움
  2. detail.status 가 종료 상태 (`completed`/`partial`/`failed*`) → `state.status='completed'` + `isHistorical=true` + **SSE 연결 스킵**
  3. 진행 중 상태 (`running`/`unknown` — metadata 미작성 상태도 포함) 또는 fetch 404 → SSE 구독으로 후속 메시지 합치기 (`seenIds` 기반 dedupe 로 boundary 중복 방어)
  4. `RunState` 에 `isHistorical: boolean` 필드 추가 — `PlaybackToggle` 이 `disabled={!run.isHistorical}` 로 라이브 비활성·과거 활성 정확 분기
- **검증**: `npm run build` 통과 (`/run/[id]` 5.73→6.16 KB). 실제 백엔드의 완료 run (`2026-05-26T14-52-34_df9eb51a`, status=completed) 호출 시 messages 12건·judge_panel 포함·humanized 필드 정상 응답 확인
- **잔여**: 과거 run 의 누적 토큰·비용은 metadata 에 아직 미저장 → judge_panel.cost_usd_estimate 만 부분 표시. 전체 비용 누적은 cost_tracker 통합 시점에 별도 정리

---

## ✅ [closed] #W-dotenv-not-loaded — FastAPI uvicorn 진입 시 .env 자동 로드 안 됨

- **발견**: 2026-06-01 (라이브 generate 호출 시 사용자 보고)
- **현상**: 메인 페이지에서 generate 클릭 → 백엔드 즉시 `ValueError: API 키 미설정. .env 에 GOOGLE_AI_STUDIO_API_KEY 또는 GEMINI_API_KEY 설정 필요.` (`gemini_client.py:74`). `run_manager._run_pipeline` 의 `GeminiClient(...)` 초기화 단계에서 예외 → SSEBroker 가 즉시 `error` 이벤트 publish + 세션 close → 프론트는 'connecting' 후 무한 대기 또는 error 표시
- **원인**: `backend/api/main.py` 에 `load_dotenv()` 호출이 없었음. CLI 스크립트(`scripts/run_full_pipeline.py`, `scripts/run_api_server.py`) 들은 모두 `load_dotenv()` 를 호출하지만, `uvicorn backend.api.main:app` 으로 직접 기동하거나 `--reload` subprocess 가 `main.py` 를 재 import 할 때는 스크립트 main() 이 실행 안 됨 → 환경변수 미주입. `.env` 자체에는 키 정상 존재
- **수정**:
  1. `backend/api/main.py` 최상단(다른 import 보다 먼저)에 `load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")` 추가. 절대 경로로 cwd 의존성 제거. 기존 import 들은 `# noqa: E402` 처리
  2. `backend/llm/gemini_client.py` `__init__` 1차 키 조회 실패 시 fallback 으로 `load_dotenv()` 한 번 더 호출 후 재조회 (이미 로드됐으면 no-op, `override=False` 기본값)
- **검증**:
  - `python -c "from backend.api.main import app"` import 시 .env 자동 로드 + 키 존재 확인 (PASS)
  - 환경변수 강제 제거 후 fallback 경로만으로 `GeminiClient()` 초기화 (PASS)
  - 회귀: backend 단위 테스트 33건 모두 PASS (테스트들은 monkeypatch / 별도 fixture 사용, .env 의존 없음 확인됨)
- **잔여**: 사용자가 uvicorn 서버 재시작 필요 (Claude 가 직접 재시작 못함). 재시작 후 `/api/health` → 정상, generate 호출 → Gemini API 호출 진입 확인. `#judge-env-key-mismatch` (Settings vs GeminiClient 키 이름 불일치) 는 별건 이슈로 그대로 유지

---

## ✅ [closed] #W-gemini-503-fallback — gemini-2.5-flash 만성 503 폴백 체인 도입

- **발견**: 2026-06-01 (라이브 generate 호출 시 사용자 보고. 1월부터 Google 측 capacity 만성 장애)
- **현상**: `gemini-2.5-flash` 503 UNAVAILABLE 빈발 → 단일 호출 실패가 그대로 파이프라인 전체 실패로 전파. 기존 `_execute_agent` 의 max_retries=1 + 0.5s sleep 만으로는 회복 안 됨
- **제약**:
  - `gemini-2.0-flash` 는 2026-06-01 retire → 폴백 후보 아님
  - 공식 마이그레이션 타겟: `gemini-2.5-flash-lite`
  - `gemini-2.5-flash-lite` 는 Google Search Grounding 미지원
- **수정**:
  1. `backend/llm/gemini_client.py` 의 `call()` 안에 모델 체인 + retry 루프 내장
     - 모델당 최대 3회 시도, exponential backoff (1s → 2s → 4s, ±30% jitter, cap 8s)
     - 503/429/5xx/UNAVAILABLE/RESOURCE_EXHAUSTED 만 retryable. 400/401/403/404 즉시 실패
     - JSON 파싱 실패는 재시도/폴백 안 함 (모델이 응답은 했음)
  2. 모델당 retry 한계 도달 시 다음 모델로 폴백. 폴백 발생 시 명시적 INFO/WARNING 로그
  3. Grounding 미지원 모델 set (`_NO_GROUNDING_MODELS = {"gemini-2.5-flash-lite"}`) 폴백 시 `use_grounding` 자동 비활성화
  4. 모델 체인 우선순위: `models=` 인자 > `model=` 인자 > `AIDEN_GEMINI_MODELS` 환경변수 (콤마 split) > default `["gemini-2.5-flash", "gemini-2.5-flash-lite"]`
  5. `last_used_model` 속성 노출 — 호출 후 실제로 응답한 모델 확인 가능 (trace 기록용)
  6. `backend/api/services/run_manager.py` 의 직박힌 `GeminiClient(model="gemini-2.5-flash")` → `GeminiClient()` 로 변경 (환경변수/default 사용)
- **마감 후 원복**: `.env` 에 `AIDEN_GEMINI_MODELS=gemini-2.5-flash` 한 줄 추가 → 폴백 없이 단일 모델로 회귀. 또는 본 환경변수 제거 시 default 체인 그대로
- **검증**:
  - 신규 단위 테스트 10건 PASS (`backend/tests/llm/test_gemini_fallback.py`):
    - retryable / non-retryable 분류, primary 성공 시 폴백 X, 503 → secondary 폴백 성공, 모든 모델 실패 시 raise, 400 즉시 실패, 환경변수 파싱, 단일 모델 비활성화, Grounding 자동 강등, JSON 파싱 실패 재시도 X
  - 전체 backend 회귀: **43건 PASS** (기존 33 + 신규 10)
- **잔여**:
  - 실제 라이브 호출 검증은 사용자가 uvicorn 재시작 + generate 1회 호출 후 확인 (Claude 직접 검증 못함)
  - `gemini-2.5-flash-lite` 가 `response_mime_type='application/json'` 을 지원한다는 가정 — 만약 미지원 신호 발견 시 `_NO_JSON_MIME_MODELS` 추가 필요 (현재까지 SDK 응답으로 확인된 사례 없음)
  - Stage 4 Judge Panel 의 Gemini Judge 는 별도 경로 (`backend/orchestrators/judge_panel.py`) 사용 — 본 폴백 체인 영향 받지 않음. Judge Gemini 503 도 동일 패턴 적용은 마감 후 검토

---

## ✅ [closed] #W-sse-live-publish-broken — 라이브 SSE 메시지가 프론트에 도달 안 함

- **발견**: 2026-06-01 (B3-S3-C fetch-then-stream 재작성 이후 사용자 보고)
- **증상**:
  - 백엔드 로그: `GET /api/stream/{run_id}` 200 OK 가 같은 run 에 대해 4회 반복 (EventSource 재연결 패턴)
  - 백엔드 파이프라인 정상 진행 (trace 디스크 기록 정상). 새로고침하면 `GET /api/runs/{id}` 로 모든 메시지 수신
  - 라이브 도중 화면에 채팅 메시지 0건 — 무한 "연결중..." 표시
- **진단 (확인된 사실)**:
  1. 백엔드 publish 이벤트명: `pipeline_start`, `agent_step`, `pipeline_complete`, `error`. stream router 가 `agent_step` 만 `convert_trace` 후 `event: chat` 으로 변환해 forward. 그 외는 그대로
  2. 프론트 listener: `chat`, `pipeline_start`, `stage_change`, `cost_update`, `judge_evaluation`, `pipeline_complete`, `error`, `ping`. **이벤트명 매핑은 정상**, mismatch 아님
  3. `SSEBroker.publish` 는 채널에 구독자가 없으면 silent drop. broker 에 채널별 message buffer 가 **부재**
  4. `GET /api/runs/{id}` 는 `metadata.json` 미작성 시 404 반환 (라이브 run 초반 metadata 미작성 상태)
- **Root cause**:
  - 라이브 시작 직후 클라이언트는 `/run/[id]` 마운트 → `fetchRunDetail` await (보통 100–300ms) → 404 catch → `subscribeLive` 호출. 이 사이에 백엔드는 이미 `pipeline_start` + 첫 `agent_step` 등을 publish 함 → broker 에 구독자 없음 → drop
  - 추가로 EventSource 재연결마다 (4회 관측) 동일 손실 누적. 재연결의 정확한 원인 (dev hot reload / strict mode 더블 마운트 / 클라이언트 cleanup) 은 환경 의존적이지만, 버퍼만 있어도 모든 재연결 케이스를 방어 가능
- **수정**:
  1. `backend/api/services/sse_broker.py` — 채널별 ring buffer (`collections.deque(maxlen=500)`) + replay 도입
     - `publish`: close sentinel 외 모든 메시지를 buffer 에 append. publish 시점에 구독자가 없어도 buffer 에 보존
     - `subscribe`: snapshot 직후 라이브 큐 등록 (asyncio single-thread 라 race 없음) → snapshot 부터 yield → 라이브 큐 처리. 새 subscriber 와 재연결 subscriber 모두 buffer 전체를 replay 받음
     - `close`: `_buffer_expires_at` 마커 설정 (TTL 30분). subscribe 가 close 마커 보면 buffer 만 회수 후 즉시 종료 (재연결 무한 대기 방지)
     - lazy GC: subscribe 진입 시 TTL 경과한 message buffer 만 정리, close 마커는 유지
  2. `backend/api/routers/stream.py` — stream gen 종료 시 `events_sent` 카운터 INFO 로그 (사용자 검증용. 손실 진단 완료 후 제거 가능)
- **검증**:
  - 신규 단위 테스트 6건 (`backend/tests/api/test_sse_buffer.py`):
    - publish-before-subscribe 시 모두 replay / 재연결 시 history 전체 replay / replay 후 라이브 메시지 / close sentinel 미버퍼링 / close 후 subscribe 빠른 종료 / TTL GC
  - 전체 backend 회귀 **49건 PASS** (기존 43 + 신규 6)
  - 프론트 `npm run build` 통과 (`/run/[id]` 6.16 kB 변동 없음)
- **잔여 / 후속**:
  - EventSource 4회 재연결의 정확한 원인은 본 fix 범위가 아님 — buffer + replay 로 메시지 손실은 모두 방어되지만, 재연결 자체가 잦으면 `cost_update` heartbeat 류 이벤트 흐름이 끊길 수 있음. 라이브 검증 시 백엔드 로그의 `events_sent=N` 값이 비정상적으로 작으면 dev hot reload / strict mode 의심
  - `metadata.json` 부재 시 404 대신 in-progress 상태로 부분 응답하는 옵션도 고려 가능 (B3-S3-D 또는 별건)
  - 임시 디버그 로그 (`stream.py` 의 `events_sent`) 는 라이브 검증 종료 후 제거 안내

---

## ✅ [closed] #W-sse-cors-blocked — /run/[id] 페이지가 "연결 중" 상태로 멈춤

- **발견**: 2026-06-04. B3-S3-C trace viewer 라이브 검증 중. 사용자가 새 탭에서 `http://localhost:8000/api/stream/{run_id}` 직접 접속 → `event: chat` 메시지가 정상 흐름. 같은 시점 `/run/{id}` 페이지는 빈 상태
- **첫 가설 (오진)**: `useRunStream` 의 `addEventListener` 이벤트 이름이 백엔드 publish 이름(`chat`, `ping`) 과 불일치
- **검증 결과 — 첫 가설 틀림**:
  - `frontend/lib/api.ts:184-202` 의 listener: `chat`, `pipeline_start`, `stage_change`, `cost_update`, `judge_evaluation`, `pipeline_complete`, `error`, `ping` 모두 등록되어 있음
  - 백엔드 실제 wire event (`backend/api/routers/stream.py`): `ping`, `pipeline_start`, `chat`, `pipeline_complete`, `error`
  - `chat`/`ping` 매칭 **정상**. `stage_change`/`cost_update`/`judge_evaluation` 은 백엔드 미발행 (dead listener, 무해)
  - `ChatMessage` 타입 (`api.ts:59-73`) 도 백엔드 `trace_converter._base` 와 12개 필드 1:1 일치
- **진짜 원인**: cross-origin (localhost:3000 → localhost:8000) CORS allow_origins 에 `http://127.0.0.1:3000` 누락. 브라우저는 `localhost` 와 `127.0.0.1` 을 별개 origin 으로 취급하므로 사용자가 후자로 프론트 접속 시 EventSource 가 silent fail (메시지 0건, error 이벤트는 data 없는 빈 Event)
- **수정**:
  - `backend/api/main.py::_cors_origins` 기본값에 `http://127.0.0.1:3000`, `http://127.0.0.1:3001` 추가
  - `CORSMiddleware.allow_credentials=True` 로 변경 (현 EventSource 는 `withCredentials` 미사용이라 즉시 효과 없지만, 향후 인증 도입 시 safe default. `allow_origins` 가 명시 리스트라 spec 위반 아님)
- **검증**:
  - 백엔드 재시작 후 사용자가 `http://localhost:3000` / `http://127.0.0.1:3000` 두 경로 모두에서 `/run/{id}` 페이지 → 라이브 메시지 도착 확인
  - 브라우저 DevTools Network 탭 → `/api/stream/{id}` 요청 → Response Headers `access-control-allow-origin` 값이 요청 origin 과 일치하는지 확인
  - 콘솔에 `Access to ... blocked by CORS policy` 빨간 에러가 사라졌는지 확인
- **재발 방지 / 교훈**:
  - **첫 가설을 코드 변경 전에 반드시 grep 으로 검증할 것**. 본 건은 사용자 진단이 "listener 이름 불일치 확정" 이었으나 grep 결과 매칭됨. 그대로 listener 이름을 바꿨다면 멀쩡한 코드를 깨뜨려 회귀를 만들었을 것
  - 명세서 (`docs/patches/2026-05-28_b3-s3-c_trace_viewer.md` §6-1 추정) 가 이벤트명을 가정으로 기술하고 있다면 외부 인터페이스는 가정으로 두지 말 것 — 백엔드 publish 호출부 grep 으로 enumerate
  - 로컬 개발 환경 CORS 는 `localhost` 와 `127.0.0.1` 양쪽 모두 포함이 default 이어야 함

---

## ✅ [closed] #W-sse-30s-disconnect — SSE stream 이 정확히 30초마다 끊김

- **발견**: 2026-06-04. `#W-sse-cors-blocked` fix 후에도 사용자 `/run/{id}` 화면이 "연결 중" 으로 멈춤. Network 탭에 같은 session 으로 `eventsource` 항목 8개 누적, 처음 4개가 **정확히 30.0s ~ 30.11s** 에 종료. heartbeat 주기 (`HEARTBEAT_SEC = 30.0`) 와 정확히 일치
- **root cause**: `backend/api/routers/stream.py::gen` 의 `asyncio.wait_for(sub.__anext__(), timeout=HEARTBEAT_SEC)` 패턴. `wait_for` timeout 시 underlying coroutine 을 cancel 하는데, 그 underlying 이 `broker.subscribe` async generator 의 `__anext__()` 라서 generator 내부 `await queue.get()` 가 `CancelledError` 를 받고 `finally` 블록 실행 → generator 종료. 다음 `__anext__()` 호출은 `StopAsyncIteration` → stream 종료. 첫 30초 안에 publish 가 없으면 무조건 끊김 (scout 의 grounding 호출이 200초 + 걸리므로 100% 재현)
- **`#W-sse-cors-blocked` 와의 관계**: CORS 도 별도 누락이 있어 fix 가치는 있었으나, **사용자의 진짜 증상은 본 30초 끊김이 원인**. 이전 진단을 부분 정정
- **수정**:
  - `backend/api/services/sse_broker.py::subscribe(session_id, heartbeat_sec=None)` — heartbeat 옵션 추가. generator **내부**에서 `asyncio.wait_for(queue.get(), timeout=heartbeat_sec)` 로 timeout 처리, timeout 시 `{"event": "ping", "data": {}}` yield 후 루프 계속. wait_for 의 cancel 이 queue.get task 에만 적용되고 generator 자체는 살아있음
  - `backend/api/routers/stream.py::gen` — 외부 `asyncio.wait_for` 제거. `broker.subscribe(session_id, heartbeat_sec=HEARTBEAT_SEC)` 호출 + `async for msg in sub:` 패턴으로 단순화. heartbeat ping 은 `else` 분기에서 그대로 forward
  - stream.py 의 unused `import asyncio` 제거
- **검증**:
  - 기존 단위 테스트 6건 (`test_sse_buffer.py`) + stream 테스트 3건 (`test_stream.py`) **9/9 PASS** — `heartbeat_sec=None` default 라 기존 호출부 회귀 없음
  - 라이브 검증: 백엔드 재시작 후 사용자 `/run/{id}` 페이지에서 SSE connection 1개가 끊김 없이 유지되고 (Status `pending`), chat 메시지가 라이브로 도착하는지
- **재발 방지 / 교훈**:
  - **async generator 외부에서 `asyncio.wait_for(__anext__(), ...)` 패턴 금지**. timeout/heartbeat 는 generator 내부에서 처리. `wait_for` 의 cancel semantic 은 wrapped awaitable 만 cancel 한다는 것 같지만, `__anext__()` 의 cancel 은 generator 의 await 지점에 들어가서 generator 상태를 종료시킨다
  - 같은 클래스의 알려진 Python 함정: `asyncio.timeout()` 컨텍스트 (3.11+) 도 generator 외부에서 쓰면 동일한 문제 발생 가능
  - 진단 교훈: Network 탭의 `eventsource` connection 종료 시간이 `HEARTBEAT_SEC` 와 일치하면 본 패턴 의심
  - 첫 가설 (listener mismatch) → 두 번째 가설 (CORS) → 진짜 (wait_for+async gen) 3단계. **표면 증상으로 root cause 추정 금지, network/timing 데이터로 확정 후 fix**

---

## ✅ [closed] #W-usestream-impure-updater — useRunStream 의 setState updater 가 Strict Mode 에서 messages 를 빈 배열로 reset

- **발견**: 2026-06-04. `#W-sse-30s-disconnect` fix 후에도 라이브 화면이 "연결 중… 첫 메시지를 기다립니다" 에서 멈춤. 새로고침하면 fetch 결과로 메시지가 보이지만 라이브 SSE 로는 화면 안 갱신
- **진단 흐름**:
  1. 백엔드 SSE 정상 (curl 45초 + native EventSource 280 chat 검증 완료)
  2. ChunkLoadError → 3000 좀비 dev 서버 → 정리
  3. 그래도 화면 멈춤. useRunStream 에 임시 console.log 5곳 추가
  4. **결정적 출력**: 매 `onChat` 1회 호출 → `setState messages= 1` → `setState messages= 0` (두 번째에서 빈 배열로 reset)
- **root cause**: `useRunStream.ts` 의 `appendUnique` 가 외부 `seenIds: Set<string>` 을 `.add()` 로 mutate. setState updater 안에서 호출됨. React **Strict Mode (dev)** 는 updater 의 순수성 검사를 위해 의도적으로 **2회 호출** 하는데, impure updater 이라 2번째 호출에서 새 메시지의 id 가 seenIds 에 이미 있어서 dedup → 빈 merged 반환 → state.messages = []
  - 본 패턴은 production 빌드에서는 동작 (Strict Mode 의 double-invoke 는 dev only) 이지만, dev 에서 라이브 SSE 검증 자체가 불가능했음
- **수정**:
  - `frontend/hooks/useRunStream.ts::appendUnique` — 외부 `seenIds` Set 제거. updater 안에서 `new Set(prev.map(m => m.id))` 로 매 호출마다 새 Set 생성 (idempotent). 의도 주석 명시
  - 더 이상 외부 Set 을 채우지 않으므로 fetch 응답 처리 시 `seenIds.clear(); for (...)` 블록도 제거 (death code)
- **검증**:
  - 사용자 시크릿 창에서 generate → /run/{id} → **라이브 채팅 메시지 정상 도착 확인**
  - 임시 디버그 로그 (5곳 `console.log`) 모두 제거
- **재발 방지 / 교훈**:
  - **setState updater 는 반드시 pure**. 외부 변수/Set/객체 mutate 금지. Closure 캡처된 가변 상태는 `useRef` 로 격리하거나, updater 안에서 prev state 로부터 매번 derive
  - **Strict Mode 의 double-invoke 는 dev 만이며 의도된 검사**. 끄지 말 것. 본 케이스처럼 production 에선 묻혀있던 버그가 노출됨
  - 진단 흐름 교훈: 표면 증상으로부터 root cause 가 **3 hop** 떨어져 있었음 (① listener mismatch 가설 → 오진 / ② CORS + 30초 끊김 fix → 부분적 / ③ Strict Mode + impure updater → 진짜). 매 단계 가설을 코드/데이터로 검증 후 다음으로 이동한 것이 결정적
  - 임시 console.log 추가 → 정확한 호출 횟수와 state 값 비교 → impure updater pattern 식별. 동일 디버깅 패턴 (`setState` 두 번 호출 + 값이 같지 않음) 은 항상 updater 순수성 의심

---

## Issue 관리 규칙

- 신규 발견 시 본 파일에 누적
- close 시 항목 삭제하지 말고 `## ✅ [closed] #...` 형식으로 변경
- 마감 후 별도 ISSUES.md 또는 GitHub Issues 로 이관 검토

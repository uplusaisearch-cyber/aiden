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

## Issue 관리 규칙

- 신규 발견 시 본 파일에 누적
- close 시 항목 삭제하지 말고 `## ✅ [closed] #...` 형식으로 변경
- 마감 후 별도 ISSUES.md 또는 GitHub Issues 로 이관 검토

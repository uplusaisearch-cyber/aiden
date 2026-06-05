# AIDEN 개발 진행률

> 이 문서는 **AIDEN 개발 과정 자체**의 공정률을 추적합니다.
> (AIDEN이 생성하는 콘텐츠나 운영 기능과는 별개)

| 항목 | 값 |
|---|---|
| **마지막 업데이트** | 2026-06-05 폴리싱 2차 (run UI 3건 — PlaybackToggle 제거 · ← 메인 좌상단 · Game-ifier→인터랙티브 빌더) 완료 |
| **전체 진행률** | **100.0%** 본구현 (57/57) + 마감 후속 1차 **7/7** + 폴리싱 2차 **1/1** (run UI 3건) |
| **현재 Phase** | Phase 1~4 본구현 완료, Phase 5 배포·라이브 검증 완료. **마감 2026-06-08** 잔여: 운영 종단 회귀(commits 9ae0424·fa7f1e1·402dfaf·3c1e5d0·ffe450a·fa08969 반영 후 1 run), 발표/결선 PT 자료(별도 채팅), (여유 시) Format Architect 인터랙티브 강화 |

---

## Phase 1: Project Scaffold ✅ (완료 — 2026-05-22)

- [x] CLAUDE.md 생성 _(2026-05-22)_
- [x] 폴더 구조 생성 (config, backend, frontend, docs, scripts) _(2026-05-22)_
- [x] config/*.yaml 4종 (brand, agents, platform, deployment) _(2026-05-22)_
- [x] backend/core 베이스 클래스 (settings, llm_clients, base_agent) _(2026-05-22)_
- [x] 9 에이전트 prompt 파일 placeholder _(2026-05-22)_
- [x] HTML 템플릿 placeholder _(2026-05-22)_
- [x] docs 4종 초안 _(2026-05-22)_
- [x] Git 초기화 + 첫 커밋 (9906b31) _(2026-05-22)_

---

## Phase 2: 9 Agents + Orchestration ✅ (완료 — 2026-05-25)

- [x] 비용 안전장치 (cost_tracker + 예산 enforcement + dry-run 모드) _(2026-05-22)_
- [x] Trend Scout system prompt 작성 _(2026-05-23)_
- [x] Audience Analyst system prompt 작성 _(2026-05-23)_
- [x] Strategy Planner system prompt 작성 _(2026-05-23)_
- [x] Writer system prompt 작성 _(2026-05-22)_
- [x] Fact-Checker system prompt 작성 _(2026-05-22)_
- [x] Devil's Advocate system prompt 작성 _(2026-05-22)_
- [x] Editor-in-Chief system prompt 작성 _(2026-05-22)_
- [x] Format Architect system prompt 작성 _(2026-05-22)_
- [x] HTML Builder system prompt 작성 _(2026-05-23)_
- [x] 플러스탭 HTML 샘플 분석 → templates/plustab_structure.md 채우기 _(2026-05-22)_
- [x] type_a.html, type_b.html 템플릿 완성 _(2026-05-22)_
- [x] base_agent.py 일반화 (PromptLoader + WhitelistedSubstitutor) _(2026-05-23)_
- [x] backend/config/agent_resources.json 신규 _(2026-05-23)_
- [x] backend/config/cdn_urls.json 신규 _(2026-05-23)_
- [x] tests/test_base_agent.py 단위 테스트 _(2026-05-23)_
- [x] data_flow_spec.md 작성 (Stage 1~3 흐름 명세) _(2026-05-23)_
- [x] trace_logger.py: 단계별 JSON + summary.jsonl _(2026-05-23)_
- [x] base_newsroom.py: 미니 state-machine 베이스 _(2026-05-23)_
- [x] topic_newsroom.py: Stage 1 오케스트레이터 _(2026-05-23)_
- [x] test_topic_newsroom.py: 단위 테스트 7건 _(2026-05-23)_
- [x] content_newsroom.py: Stage 2 오케스트레이터 (iter 1/2/3 토론) _(2026-05-23)_
- [x] trace_logger.py: highlight 4종 추가 (Writer/FC/DA/Editor) _(2026-05-23)_
- [x] test_content_newsroom.py: 단위 테스트 10건 _(2026-05-23)_
- [x] Step 2.5: gemini_client.py + concrete_agents.py + 실행 스크립트 2종 _(2026-05-25)_
- [x] Step 2.5: Topic Newsroom 실제 LLM 1회 실행 _(2026-05-25, 재시도)_
- [x] Step 2.5: Content Newsroom 실제 LLM 1회 실행 (iter 1→2→3 approved) _(2026-05-25, 재시도)_
- [x] Step 2.5: early_integration_report.md 초안 + 재시도 결과 _(2026-05-25)_
- [x] Gameifier 오케스트레이터 (Stage 3) _(2026-05-25)_
- [x] FullPipeline 통합 (3 Newsroom) _(2026-05-25)_
- [x] run_full_pipeline.py E2E 스크립트 + HTML 래퍼 _(2026-05-25)_
- [x] test_gameifier.py + test_full_pipeline.py 통합 테스트 _(2026-05-25)_
- [x] 9 에이전트 실제 LLM E2E 완주 + final_output.html _(2026-05-25)_
- [x] data_flow_spec.md §6 Stage 3 보강 _(2026-05-25)_
- [x] 묶음 3 Step 1 우선순위 1: P2 R3 fact_checker iter3 verification_log 누락 수정 _(2026-05-25)_
- [x] 묶음 3 Step 1 우선순위 2: 재현성 E2E 3회 (맛집·안전·AI트렌드, 모두 PASS) _(2026-05-25)_
- [x] 묶음 3 우선순위 3: Judge Panel 오케스트레이터 (Stage 4) _(`backend/orchestrators/judge_panel.py` + `_call_gemini_judge_default`/openai/anthropic 3 모델, weighted_total·outlier·consensus 산출)_
- [x] 묶음 3 우선순위 4: 어드민 UI (system prompt 편집기) _(B3-S3-E Persona Lab — Monaco Editor + history/restore/rollback, 2026-06-05)_
- [x] 콘솔 end-to-end 통합 테스트 _(재현성 E2E 3회 + B3-S3-C 라이브 검증 + 운영 라이브 9 에이전트 완주 `2026-06-05T00-50-24_c98b5ddc`)_

---

## Phase 3: API Server ✅ (완료 — 2026-06-04)

- [x] FastAPI 기본 서버 구조 _(`backend/api/main.py` + 9 routers: generate/stream/runs/judges/personas/prompts/admin_keys/admin_registry)_
- [x] POST /api/generate 엔드포인트 _(`routers/generate.py` — 카테고리/자유입력 → run_manager 비동기 launch)_
- [x] GET /api/stream/{job_id} SSE 엔드포인트 _(`routers/stream.py` + `sse_broker` ring buffer 500 + heartbeat 30s + replay)_
- [x] 에이전트 trace 실시간 발행 _(`pipeline_start`/`chat`/`stage_change`/`cost_update`/`judge_evaluation`/`pipeline_complete`/`error` 이벤트, commit 4332407 라이브 검증 통과)_
- [x] CORS 설정 _(`API_CORS_ORIGINS` env + Vercel origin 연동, `allow_credentials=True`, commit 4332407)_
- [x] 에러 핸들링 _(judge 404 분기 + `error.tsx`/`not-found.tsx`/`global-error.tsx` 3-layer + Gemini 503/빈응답 폴백 commit 87653d2)_

---

## Phase 4: Frontend + Admin ✅ (완료 — 2026-06-05)

- [x] Next.js 14 프로젝트 셋업 _(2026-05-26 · B3-S3-A)_
- [x] Tailwind + shadcn/ui 설정 _(2026-05-26 · B3-S3-A)_
- [x] 메인 페이지: 카테고리 선택 UI (프리셋 4 + 자유 입력) _(2026-05-26 · B3-S3-A/B)_
- [x] 트레이스 대시보드 (에이전트별 색상 채팅 버블, SSE 연결) _(2026-05-28 · B3-S3-C)_
- [x] 최종 콘텐츠 미리보기 (iframe) _(2026-06-04 · B3-S3-D)_
- [x] 심사 결과 카드 3개 (Radar + 3 ModelScoreCard, 카운트업·outlier·consensus 포함) _(2026-06-04 · B3-S3-D)_
- [x] 어드민: 운영 콘솔 셸 + 사이드바 (`/admin` 5개 메뉴) _(2026-06-05 · B3-S3-E)_
- [x] 어드민: Persona Lab — 12 에이전트 system prompt 편집 + 저장/기본값 복원/버전 히스토리/롤백 (A1) _(2026-06-05 · B3-S3-E)_
- [x] 어드민: Persona Lab 에디터 Monaco Editor 적용 (markdown, vs-dark 다크 테마, SSR-safe `next/dynamic`) _(2026-06-05)_
- [x] 어드민: API 키 페이지 — 런타임 메모리 override(>env) 방안 A, 평문 키 노출 0 + 마스킹 (A2) _(2026-06-05 · B3-S3-E)_
- [x] 어드민: 발행 이력 레지스트리 — `data/topic_registry.json` CRUD + Topic Scout `{{PUBLISHED_TOPICS}}` 동적 주입 (A3) _(2026-06-05 · B3-S3-E)_
- [x] 어드민: 운영 옵션 페이지 — 실동작/장식/BLOCKED 뱃지 (실동작 설정은 .env/config 안내) _(2026-06-05 · B3-S3-E)_

---

## Phase 5: Deploy + Polish ⬜

- [x] Vercel 배포 (Frontend) — GitHub repo `uplusaisearch-cyber/aiden` 연결, 자동 재배포 파이프라인 동작 _(2026-06-05)_
- [x] Railway 배포 (Backend) — Procfile 단일 워커 `+$PORT` 바인딩, `.python-version` 3.11, `railway.json` healthcheck=`/api/health`. SSE 버퍼링 없음·9 에이전트 완주·iframe 서빙 운영 실측 PASS _(2026-06-05)_
- [x] 환경변수 설정 — CORS `API_CORS_ORIGINS` 로 Vercel origin 연동, GEMINI/OpenAI/Anthropic 키 Railway 환경변수 + 런타임 override (A2) _(2026-06-05)_
- [x] fix: final-html iframe 404 — `judges.py` 메타 url 을 `/api/runs/{id}/output` 으로 일원화, `/runs` StaticFiles mount 제거 (배포 환경 `runs/` 부재 우회) _(2026-06-05)_
- [x] 프리셋 4개 카테고리 라이브 테스트 — 운영 환경 food 카테고리 9 에이전트 완주(`status=completed`, 319초, weighted_total=67.2, failed_models=[]) _(2026-06-05)_
- [ ] 프롬프트 튜닝 사이클 (마감 후 후보)
- [ ] 데모 시나리오 검증 (별도 채팅)
- [ ] 발표 자료 작성 (별도 채팅)
- [ ] 메타 산출물 정리 (아이데이션 트레이스, 아키텍처 다이어그램)

---

## Phase 5+: 마감 6/8 전 폴리시 ⬜ (후속 트랙)

- [x] **Judge Panel 역할 재정의** — "공모전 심사위원" → "플러스탭 콘텐츠 품질 평가 위원" (10/11/12_judge_*.md 활성본 + `_defaults/` snapshot 동시 갱신). 평가 5축·가중치·산출식·JSON 스키마 무변경 _(2026-06-05, commit 9ae0424)_
- [x] **9 에이전트 발화 고도화** — `personas.yaml` prefix/suffix 풀 3→**8**개 확장, A-3 톤 가이드대로 차별화(scout 들뜸 / analyst 냉정 / planner 결단 / writer 몰입 / factchecker 의심 / devils 도발 / editor 균형 / architect 설계 / builder 담백). humanizer md5-seed 결정성 유지. 9 md 텍스트 필드(reasoning/angle/summary/rationale/critical_issues.problem 등)에 "구체 인용·2~4문장·일반론 금지" 지시 추가 _(2026-06-05, commit fa7f1e1)_
- [x] **trace_converter 키 정합** — `_convert_devils` 의 `issue` → 실제 스키마 키 `problem` 우선 + `issue` fallback, `_convert_architect` 의 `rationale` → `format_analysis` 우선 + `type_reasoning`/`rationale` fallback. 하드코딩 "까겠습니다" 제거(personas suffix 위임). devils/architect body_text 가 항상 빈 문자열이던 잠복 버그 해소 _(2026-06-05, commit fa7f1e1)_
- [x] **Part B 콘텐츠 품질** — Writer 출처 채택·배제 규칙(미래 날짜 출처·익명/비특정 도메인 배제, 공신력 소스 우선), Fact-Checker 위반 강제 적시(unverified/corrected status 하향 + summary 명시, 검증 로직 무약화), Judge 5축 정성 앵커(발행가능/주의/재작성 3단계, 수치 컷 미사용). 가중치·산출식·outlier·JSON 스키마 무변경 _(2026-06-05, commit fa7f1e1)_
- [x] **B3-S3-F 에이전트 상세 모달** — 트레이스 버블 클릭 → 모달, 같은 agent_id 의 iter별 메시지를 Base UI Tabs 로 묶음. Writer(본문 word-diff 좌/우 컬럼) / Fact-Checker(verified·unverified·corrected 색구분) / Devils(문제→제안 쌍 카드) / Editor(accepted·rejected 2열) 전용 렌더러 4종 + 나머지 5종 `GenericDetail` 공통 카드. Judge 버블 미적용(B3-S3-D 별도 시각화). 백엔드 0 변경, 프론트 단일 commit _(2026-06-05, commit 402dfaf)_
- [x] **global-error.tsx 최후 경계** — `app/global-error.tsx` 신규(인라인 minimal style, system-ui, 자체 `<html><body>`). `reset()` 미사용 + `window.location.reload()` (global 상황 회복 불가 케이스 대비). 새로고침 버튼 1개에만 브랜드 핑크 액센트. `error.tsx`/`not-found.tsx` 는 commit 2d7dfb1 본구현 그대로 유지(명세 요구사항 이미 충족) _(2026-06-05, commit 3c1e5d0)_
- [x] **토큰·비용 실측 종속 저장** — `cost_tracker._runs[run_id]` 에 `prompt_tokens`/`completion_tokens` 필드, `record()` 시그니처에 토큰 keyword 인자. `llm_clients.py:338` 호출에서 SDK 실측 토큰(`p_tok`/`c_tok`) 전달. `trace_logger.write_metadata(cost_summary=)` 인자 추가 → `metadata["cost"]` 에 newsroom 실측 + judge 추정 breakdown 저장(`is_actual_tokens` 플래그). `RunDetail.cost: dict \| None` 신규 필드로 API 노출. **NowPlayingPanel 의 UsageCard 제거**(4→3 카드). **SSE 보호 최우선** — `stream.py` / `useRunStream.ts` / `sse_broker.py` diff 0, `onCostUpdate` 리스너+state 필드는 dead 데이터로 유지. backend 49 PASS, npm build PASS _(2026-06-05, commit ffe450a)_
- [x] **(폴리싱 2차)** UI 3건 — PlaybackToggle 컴포넌트 삭제 (no-op 토글 제거) / ← 메인을 헤더 우측 → 풀폭 슬림 top bar 좌상단 (가운데 헤더 좌측 단일 정렬로 정리) / `personas.yaml` `stages.gameifier.display_name` "Game-ifier" → "인터랙티브 빌더" (internal key 불변). 에러/폴백 ← 메인 4곳(`run/[id]:64,99` / `error.tsx:46` / `not-found.tsx:20`) 보존. npm run build PASS _(2026-06-05, commit fa08969)_
- [ ] (마감 점검) 배포 안정성 — 운영 환경에 fa7f1e1·402dfaf·3c1e5d0·ffe450a 반영 후 1 run 회귀 (발화 다양성·모달·Judge 앵커·`metadata.cost` 섹션 + `RunDetail.cost` 종단 검증)
- [ ] (여유 시) Format Architect 인터랙티브 요소 지시 강화 — C 타입 채택률·본문 부합도 개선
- [ ] 발표/결선 PT 자료 — 별도 채팅에서 진행

---

## 🧭 의사결정 로그

> 각 결정에는 **날짜**와 **이유**(가능하면)를 함께 기록합니다.

| 날짜 | 결정 | 비고 |
|---|---|---|
| 2026-05-22 | **어드민 옵션 C 채택** — system prompt 편집기 1개만 구현 | 슬라이더/A:B 테스트는 발표 컨셉으로만 다룸 (구현 X) |
| 2026-05-22 | **토론 max 3 iteration** | 비용 + 발표 시간 + 품질 수렴 절충점 |
| 2026-05-22 | **모델 배치**: Gemini 2.5 Pro = 의사결정 에이전트 / Flash = 페르소나 에이전트 | 비용 최적화 + 의사결정 품질 확보 |
| 2026-05-22 | **Grounding 범위**: Trend Scout + Fact-Checker만 | 외부 사실 의존 단계에만 한정해 비용/지연 통제 |
| 2026-05-22 | **인터랙티브 템플릿 5종**: Quiz, Calculator, Scenario Sim, Compare Slider, Checklist | 플러스탭 콘텐츠 다양성 확보 |
| 2026-05-22 | **3-Model Judge Panel**: Gemini 2.5 Pro + GPT-5 + Claude Opus 4.7 | 다중 LLM 교차 평가로 단일 모델 편향 회피 |
| 2026-05-22 | **카테고리 입력**: 자유 입력 + 프리셋 4종 (맛집/AI트렌드/안전/문화) | 데모 안정성 + 자유도 양립 |
| 2026-05-22 | **비용 안전장치 도입**: 월 $15 / 일 $2 / run $0.50 / run당 30콜, `LLMBudgetExceeded` 즉시 차단, `SAFETY_MODE=dry_run` 무비용 디버깅 | 대회/데모 중 토론 폭주로 인한 과금 사고 방지 |
| 2026-05-22 | **플러스탭 디자인 토큰 실측 확정**: `primary=#ff2e98`, `body=#181a1b`, `sub=#66707a`, `sub2=#525960`, `card-bg=#f9fafb`, `border-light=#e7ebee`. 템플릿 변수 치환은 단순 `str.replace` 만 사용 (Jinja/Mustache 루프 금지) | 실제 샘플 HTML 분석으로 추정값 폐기. 단순 치환 방침은 비개발자도 템플릿 수정 가능하게 하기 위함 |
| 2026-05-22 | **Devil's Advocate 라운드별 차등**: 비판 개수 5/3/1 + threshold 7/6/5 | 라운드 진행될수록 발산→수렴→결정타. 4개·6개 같은 가변 개수 허용 시 LLM 이 안정적이지 못해 명시적 고정 |
| 2026-05-22 | **Writer 톤 참조**: 외부 파일(`docs/samples/content_voice_examples.md`) `{{TONE_REFERENCE}}` placeholder 로 주입 | 톤 가이드를 system prompt 에 인라인하면 비개발자 수정이 불편. 별도 파일로 분리하여 텍스트 편집만으로 톤 튜닝 가능 |
| 2026-05-22 | **Editor 강제 종료**(iter 3 + DA fail): `approved` + `known_weaknesses` 명시 | 무한 루프 방지. 약점을 숨기지 않고 발표/심사 단계의 투명성 카드로 활용 |
| 2026-05-22 | **Format Architect placeholder 는 `render_zone=outside_comment` 강제** (HTML 주석 내부 치환 방지) | type_a/b.html 의 헤더 주석에도 `{{VAR}}` 가 등장하므로, 주석 내부에서 치환되면 디버깅 혼란 발생 |
| 2026-05-22 | **묶음 1→2 핸드오프 TODO 는 `docs/NEXT_BUNDLE_NOTES.md` 참조** | 묶음 1 진행 중 발생한 묶음 2 작업 요건(HTML Builder render_zone 룰, base_agent TONE_REFERENCE 치환, 오케스트레이터 설계)을 한 곳에 모아 컨텍스트 이전 손실 방지 |
| 2026-05-23 | **묶음 1 검토 패치 16건 적용 완료**: DA(입력 category 추가, critical_issues 개수와 pass_threshold 독립 명시, carried_over iter 1=[] 명시) / Editor(비판 수용 규칙 라운드별 차등 3·2·1, accepted·rejected_critiques.issue 객체화, revision_instructions 배열화, final_content 기반은 annotated_draft, editorial_decision 톤 강화, iter 3 강제 종료 시 known_weaknesses 필수 포함 항목 명시) / Format Architect(base_layout 필드 추가, 카테고리 "기타" 처리 규칙) / Writer(editor_instructions·revision_notes 배열화, strategy 활용 가이드, iter 2+ category 일관성) / Fact-Checker(annotated_draft 에 fact_claims 유지+status 메타, [출처:] 삽입 위치 규칙, confidence_score 계산식 차등 corrected -1 / unverified -2) | 1차 초안 검토에서 발견된 스키마 정합성·라운드별 운영 일관성·관측 가능성 이슈 일괄 정리 |
| 2026-05-23 | **base_agent 치환 화이트리스트 강제 결정 (옵션 B)**: `placeholder_locations` 매핑 외 `{{VAR}}` 는 무시 → 주석 자동 보호. 마커 통일 유지 | 주석 안 변수명을 문서화 목적으로 보존하면서도 의도치 않은 치환 사고를 차단. 묶음 2 base_agent.py 구현 시 적용 |
| 2026-05-23 | **묶음 2 Step 1 완료**: 4개 prompt 신규 작성 (Trend Scout / Audience Analyst / Strategy Planner / HTML Builder). 묶음 1 검토 패턴 적용(category 입력 일관, 입출력 키 매칭, 항목별 배열화, AI 클리셰 금지 명시). NEXT_BUNDLE_NOTES.md §5의 5건 미정사항 모두 확정 적용: (1) placeholder_locations.location=dotted notation, (2) image_descriptions=alt+이미지 생성 프롬프트 통합, (3) placement 구체화=between_section_N_and_N+1, (4) CALCULATOR formula=mathjs 사용/eval 금지, (5) Grounding 호출 단위=draft 전체 1회 | Topic Newsroom + Game-ifier + HTML Builder 진입 전 prompt 계층 확정 |
| 2026-05-23 | **묶음 2 분할 진행 결정**: Step 1=4개 prompt 신규 작성(이번 단계 완료), Step 2(다음)=base_agent.py 일반화(TONE_REFERENCE + placeholder 화이트리스트 치환), Step 3(다다음)=오케스트레이터 3개(Topic Newsroom + Content Newsroom + Game-ifier), 묶음 3(별도)=Judge Panel + 통합 테스트 | 한 번에 묶어 처리 시 검토 단위 비대화. 단계별 commit + 검토 사이클 유지 위함 |
| 2026-05-23 | **묶음 2 Step 1 검토 패치 13건 적용 완료**: Trend Scout(target_date 활용 명시, category 자유 입력 처리, sources 체인 흐름 주석) / Audience Analyst(오케스트레이터 전달 방식 명시, angle_suggestion 참조 흐름 주석) / Strategy Planner(의사결정 로직 데드락 방지 rule 5 + angle_suggestion 참조 rule 6 추가, final_topic.category 추가, data_grounding.source 객체화, Trend Scout 결과 개수 방어 규칙) / HTML Builder(sample 파일 누락 시 대응, html escape 모순 해소, swiper 라이브러리 CDN 명시, 이미지 URL default 처리=placeholder URL) | 묶음 2 Step 1 4개 prompt 1차 검토에서 발견된 스키마/규칙 정합성·런타임 안전성 이슈 일괄 정리 |
| 2026-05-23 | **묶음 2 Step 2/3 진입 전 미정사항 3건 NEXT_BUNDLE_NOTES §7로 정리**: 7-1 외부 CDN URL config화(Step 2 검토), 7-2 실제 이미지 URL 주입 시점(Step 3 검토), 7-3 에이전트 간 데이터 흐름 명세(Step 3 필수) | Step 2/3 진입 시 컨텍스트 손실 없이 의사결정 이어가기 위함 |
| 2026-05-23 | **묶음 2 Step 2 완료: base_agent.py 일반화** — PromptLoader(`{{KEY_NAME}}` placeholder를 `backend/config/agent_resources.json` 매핑에서 자동 주입, file/inline source_type 지원, 매핑 없는 placeholder는 보존, 파일·JSON 오류는 경고+빈 매핑) + WhitelistedSubstitutor(Format Architect의 `placeholder_locations` + `render_zone="outside_comment"` 화이트리스트 기반 치환, HTML 주석 영역은 정규식 우회로 보존). 결정 A(CDN URL config화): `backend/config/cdn_urls.json` 분리 생성, prompt 직접 참조는 Step 3 또는 별도 패치. 결정 B(placeholder 일반화): TONE_REFERENCE 외 확장 가능 구조. 단위 테스트 9건 통과(PromptLoader 5 + WhitelistedSubstitutor 4). 기존 `Agent` 클래스도 PromptLoader 경유로 치환 적용. | 묶음 1 §6 결정사항(화이트리스트 치환·주석 보호)과 Writer의 `{{TONE_REFERENCE}}` 주입을 단일 메커니즘으로 통합. 이후 placeholder 신규는 config json 한 곳에만 등록 |
| 2026-05-23 | **묶음 2 Step 3-1 완료: Topic Newsroom 오케스트레이터 + 트레이스 로깅 기반 구축**. 설계 결정 4건 확정: (1) 이미지 URL은 placeholder 그대로(별도 생성 에이전트 없음, MVP) (2) 오케스트레이터는 자체 mini-state-machine 클래스(BaseNewsroom 상속 구조) (3) 트레이스 로그는 단계별 JSON + summary.jsonl + metadata.json(`runs/{ts}_{run_id}/` 구조) (4) Step 3 분할 3-1/3-2/3-3. `docs/architecture/data_flow_spec.md` 신규(9 에이전트 입출력 매핑 + Stage 1↔2↔3 핸드오프 규칙 + 에러 처리 원칙). TraceLogger(agent별 highlight 추출 — Step 3-1은 Scout/Analyst/Planner 3종, Step 3-2/3-3에서 나머지 6종 추가 예정). BaseNewsroom(`_execute_agent`로 트레이스+재시도+에러 처리 캡슐화, 오케스트레이터는 절대 raise 안 함). TopicNewsroom(Stage 1 단방향, summary/search_queries_used 의도적 제외, target_date 미전달 시 오늘 date.today()). 단위 테스트 7건 통과(happy path, trace 생성, 입력 매핑 2건, scout 실패, target_date default, 예외 캡처). | data_flow_spec.md 로 §7-3 데이터 흐름 명세 해소. §7-2 이미지 URL은 placeholder URL default 유지 결정. 묶음 1·2 Step 1·2 산출물(prompts + PromptLoader + WhitelistedSubstitutor) 위에 Stage 1 풀스택 동작 가능 |
| 2026-05-23 | **묶음 2 Step 3-2 완료: Content Newsroom 오케스트레이터 (iter 1/2/3 토론)**. 설계 결정 3건 확정: (1) 종료 출력은 Editor 전체 (final_content는 호출자가 추출) (2) 에이전트 실패 시 강제 approved — partial 결과 + trace fail 명시 + `_orchestrator_forced` 플래그 (3) Fact-Checker는 매 iter 재실행 (Editor confidence_score 트리거 정확도 우선). 종료 조건 3가지: (a) editor.decision==approved 즉시 (b) iter 3 도달 시 강제 종료(needs_revision이어도 `_coerce_approved_at_iter3`로 approved + known_weaknesses 보강) (c) 에이전트 실패 시 `_force_approve`. iter 2+ Writer 입력에 previous_draft/factcheck_log/critique/editor_instructions, DA 입력에 previous_critiques/editor_response 조립 (data_flow_spec §4-2 그대로). TraceLogger highlight 확장: Writer(draft v + 섹션 수), FC(confidence + verified 비율), DA(critique 수 + 평균 score + pass), Editor(decision + accepted/rejected 수). 단위 테스트 10건 통과(happy 2 + force termination 1 + agent failure 2 + input assembly 3 + trace 2). 전체 회귀 26건 통과(base_agent 9 + topic_newsroom 7 + content_newsroom 10). | Stage 2 풀스택 동작 가능. Step 3-3(Game-ifier + 전체 통합) 진입 준비 완료 |
| 2026-05-25 | **묶음 2 Step 2.5 부분 완료 (P0 차단 발견)**: 코드 5종 생성(gemini_client + concrete_agents + scripts 2종 + early_integration_report). 실제 Gemini 호출 4회 시도, 모두 Trend Scout 단계에서 실패. **발견된 P0 차단 3건**: (1) 명세서 default 모델 `gemini-2.0-flash` 가 신규 사용자에게 404 (deprecated) (2) `google-generativeai` 패키지 자체가 deprecated (FutureWarning, "google-genai 로 마이그레이션 권고") (3) Gemini 2.5 의 grounding (`google_search`) tool 을 deprecated 라이브러리에서 호출 불가 — 4가지 형식 모두 거부됨(`google_search_retrieval` 문자열·`google_search` 문자열·dict form·protos). **사용자 지시 준수**: Topic 실패해도 Content 강제 진행 안 함 → Content Newsroom 미실행. 비용 ~$0 (generation 도달 전 실패). 오케스트레이터 graceful degrade 동작은 의도대로 검증됨(`_force_approve` 경로 정상). | Step 2.5 의 의도(통합 이슈 조기 발견) 달성. 권장 후속: `google-genai` 신규 패키지로 `gemini_client.py` 재작성. Step 3-3 진입 전 사용자 결정 필요(방안 A 마이그레이션 / B grounding 비활성 보조 검증 / C v2 로 보류). 상세는 docs/early_integration_report.md |
| 2026-05-25 | **묶음 2 Step 2.5 재시도 완료 (방안 A 채택, 모든 P0 해소)**: 패키지 `google-generativeai 0.8.6` → `google-genai 2.6.0` 마이그레이션. `gemini_client.py` 전체 재작성(`genai.Client(...).models.generate_content(...)` 신규 SDK 패턴 + `types.Tool(google_search=types.GoogleSearch())` grounding + `_extract_text()` candidates fallback). 모델 default `gemini-2.5-flash`로 변경(client 상수 + 스크립트 양쪽). **Grounding + JSON 충돌 해결 = 옵션 B**: grounding 사용 시 `response_mime_type` 미사용 + `JSON_FORCE_SUFFIX` 로 prompt 기반 JSON 강제. **실행 결과**: Topic Newsroom completed(run `2026-05-25T05-52-32_4c4f0b29`, 3 호출, 한글 출력 보존, final_topic.title="편의점 신상 디저트, 우리 가족 최애템 TOP5"). Content Newsroom completed(run `2026-05-25T05-53-50_7eba2b37`, iter 1→2→3 approved, Editor 자체 approved=orchestrator coerce 미발생, DA critique 5→3→1·pass False→False→True 라운드별 차등 실측 검증, 503 1회→retry 정상 흡수). 총 16 API 호출 ~$0.005-0.015. **일관성 체크리스트 전 항목 통과**(trending_topics 3개·verdict.top_choice 매칭·final_topic 키 누락 없음·Writer fact_claims·FC `[출처:]` 마커·DA critical_issues=5·pass_threshold bool·Editor decision enum). **신규 P0 차단 0건**, P2 관찰 1건(FC iter3 verification_log 비어있음 — Writer iter3에서 fact_claims 제거됐을 가능성), P3 정보 1건(503 retry로 흡수). **학습**: SDK·모델·API 표면처럼 빠르게 변하는 부분은 명세서 작성 시 최신 docs 확인 필수. 조기 통합으로 Step 3-3 진입 전 통합 위험 제거. | Step 3-3(Game-ifier + 전체 통합) 진입 가능. P2 관찰 1건은 prompt 패치 차원에서 별도 검토 (차단 아님) |
| 2026-05-25 | **묶음 2 Step 3-3 완료: Game-ifier + FullPipeline + 9 에이전트 E2E 완주**. 설계 결정 3건: (1) 통합 범위 CLI 만 (FastAPI/UI 는 묶음 3) (2) 실제 LLM E2E 전체 9 에이전트 실행 (발표용 메타 산출물 1호 확보) (3) HTML 검증은 브라우저 (final_output.html 스탠드얼론 래퍼). **Gameifier**: Format Architect → HTML Builder 단방향, 실패 시 `_fallback_html`(Editor.final_content 를 plain HTML 변환 + known_weaknesses 노출). **FullPipeline**: 단일 TraceLogger 로 3 Newsroom 통합, base_order 자동 분배(1-3 / 4-7 iter suffix / 8-9). **단위 테스트 10건 추가** (gameifier 6 + full_pipeline 4) — 전체 회귀 **36건 통과** (명세서 표기 37건은 카운트 오차, 실제 36건). **실제 LLM E2E 1회 완주** (run `2026-05-25T06-16-20_1bc88d21`, 카테고리 맛집): status=completed, 17 trace 파일, duration 372초, 18 호출(1× 503 retry 흡수), Stage 2 iter 3 자체 approved(orchestrator coerce 미발생, DA 5→3→1·pass False→False→True), **Format Architect 가 CALCULATOR 인터랙티브 자체 선택**(type=C, base=A), HTML Builder 3 subs·0 preserved·0 warnings. final_output.html 6664 bytes: mathjs CDN·data-input-id·plustab-interactive 모두 존재, `[출처:]` inline 마커 5개, 한국어 보존, charset utf-8. **최종 제목**: "가족 식비, 매달 50만원 아끼는 법". 신규 P0/P1 0건, P2 1건(FC iter 3 verification_log=[] 패턴 재발), P3 1건(503 retry 흡수). | 9 에이전트 실제 LLM 통합 첫 완주. **발표용 메타 산출물 1호** = `runs/2026-05-25T06-16-20_1bc88d21/` 전체. 묶음 3(FastAPI + Next.js UI) 진입 가능. 잔여 Phase 2 항목: Judge Panel + 콘솔 e2e 통합 테스트 |
| 2026-05-28 | **B3-S3-C 트레이스 뷰어 완료**: `/run/[id]` 페이지 본격 구현 (3-컬럼: StagePanel · ChatStream · NowPlayingPanel · PlaybackToggle). 결정 5건: (1) **페르소나 키 = ChatMessage.agent_id 짧은 형태**(`scout`/`writer`/...) — 기존 trace_converter / `AgentId` 타입과 호환, 풀네임은 `aliases` 로 흡수 (2) **humanizer 룰베이스**(md5 시드 결정론) — personas.yaml 의 prefix/suffix 옵션을 raw 텍스트 해시로 선택, `_MAX_LEN=280` 캡 (3) **humanized 필드는 ChatMessage 에 옵셔널 추가**(default `""`) — RunDetail/recentRuns 회귀 없음 확인 (4) **SSE 이벤트명은 백엔드 현실 채택**(`chat`/`pipeline_start`/`pipeline_complete`/`cost_update`) — 명세 §6-1 의 `agent_start`/`chat_message`/`agent_end`/`run_complete` 는 미존재이므로 hook 에서 백엔드 이벤트명에 맞춤 (5) **테스트 위치는 `backend/tests/api/`**(`pyproject.toml` 의 testpaths 와 일치, 명세 §11 의 `tests/test_*.py` 는 pytest 미수집 경로). **신규 단위 테스트 12건 PASS** (humanizer 8 + personas API 4), 전체 API 회귀 33건 PASS. **`npm run build` 통과**(타입 에러 0, `/run/[id]` 5.73 kB). 변경 파일: backend 6(personas.yaml/humanizer.py/trace_converter.py/schemas/trace.py/routers/personas.py/main.py) + 테스트 2 + frontend 7(lib/personas.ts·api.ts·hooks/useRunStream.ts·components/run/4종·app/run/[id]/page.tsx). | B3-S3-D(Judge 시각화)·B3-S3-E(Persona Lab UI) 진입 가능. 수동 검증(§12) 사용자 직접 수행 필요 |
| 2026-06-04 | **B3-S3-D 후속 fix: 진행 중 run Judge Panel 대기 UI + 자동 폴링**. 라이브 generate 검증 중 발견 — 파이프라인 진행 중이거나 Stage 4 미완료 상태에서 하단 "🎯 판정" 탭이 빨간 에러("Judge Panel 결과를 불러오지 못했습니다. API 404 ... judge_panel.json 없음") 를 노출. 백엔드 404 + detail 은 그대로 유지(spec 정합), **프론트 분기만 보강**: `JudgePanel.tsx` 에 `JudgePanelPending` 컴포넌트 신규 (⏳ + 3-dot pulse + 안내 문구) + error.message 에 `"judge_panel.json"` 포함 시 Pending UI 로 전환 + `useQuery refetchInterval: 15_000` (data 도착 시 자동 stop) + `retry: false` (404 retry 대신 폴링이 그 역할). 파이프라인 완료 → judge_panel.json 작성 → 다음 폴링 사이클(최대 15초)에 자동으로 결과 UI 로 전환되어 사용자 새로고침 불필요. final-html 쪽은 백엔드가 이미 `{available:false}` 200 응답 → 기존 `NotAvailable` UI 그대로 동작(회귀 0). | 라이브 발견-fix 사이클 1건. 추후 결과물 iframe 탭에도 동일 폴링 적용은 사용자 요청 시. |
| 2026-06-04 | **B3-S3-D 완료: Judge 시각화 + 결과 HTML iframe 미리보기 통합**. 명세서: `docs/patches/2026-06-04_b3-s3-d_judge_visualization.md`. **백엔드**: (1) `run_manager.py` 에 `_apply_standalone_html_wrapper` + `final_output.html` 저장 — CLI `scripts/run_full_pipeline.py` 와 byte-identical wrapper (literal 복사로 단일 출처). (2) `main.py` 에 `/runs` StaticFiles mount → `/runs/{id}/final_output.html` 직접 접근 가능 (path traversal 차단 확인). (3) `schemas/judge.py` 재작성: `JudgeResult` / `ModelEvaluation` / `CriterionScore` 신규 스키마. (4) `services/judge_adapter.py` 신규: raw judge_panel.json → JudgeResult 변환 (per-model `is_outlier` = 5축 중 1개라도 \|score - mean\| > 1.5σ, `consensus_level` = max stdev 기준 high/medium/low, `comment` = verdict + 강점 + 약점 한 줄 합성). (5) `routers/judges.py` 교체: `GET /api/runs/{id}/judge` 새 스키마 + `GET /api/runs/{id}/final-html` 메타 (available/url/size_bytes). **5축 키 결정**: 명세서의 fluffy 표기(factuality/novelty/clarity/completeness/interactivity) 대신 실측 judge_panel.json 의 dimension 명(topic_fit/content_quality/interactivity/tone_authenticity/timeliness_trust) 그대로 사용 — 데이터 진실 우선. Korean 라벨은 `AXIS_META`(주제 적합성·콘텐츠 품질·인터랙티브·톤 진정성·시의성·신뢰) 매핑. **테스트**: `test_judge_endpoint.py` 5건 PASS (200/3 evaluations, 404, outlier 정확성, consensus 경계 high/low, final-html 메타). 백엔드 전체 회귀 **56/56 PASS** (기존 51 + 신규 5). **프론트엔드**: (6) `types/judge.ts` 에 `JudgeResult`·`ModelEvaluation`·`CriterionScore`·`FinalHtmlMeta`·`AXIS_META`·`MODEL_COLORS`·`MODEL_DISPLAY_NAME` 추가 (기존 raw 미러 `JudgePanelResult` 는 RunDetail 호환 위해 유지). (7) `lib/api.ts` `fetchJudge(runId)` + `fetchFinalHtmlMeta(runId)`. (8) `hooks/useCountUp.ts` 신규 — easeOutQuart 0→target 1.2s. (9) `components/run/RadarChart.tsx` — Recharts 5축 + 3 모델 시리즈 + aggregate (strokeWidth 3 / dashed 강조), stagger animationBegin 0/150/300/450ms, 호버 시 4-value tooltip. (10) `components/run/ModelScoreCard.tsx` — 모델별 액센트 좌측 라인, overall 카운트업(text-5xl), aggregate 대비 ±delta, 5축 가로 게이지 (mount transition 700ms), outlier 시 빨간 border + pulse dot + tooltip "다른 평가자 대비 ±1.5σ 이상", 코멘트 180자 더보기. (11) `components/run/JudgePanel.tsx` — 헤더 fade-in slide-in / 차트·카드 stagger delay-150/300, AggregateOverall(text-6xl) 점수 색 8+ 녹색 / 6-8 노랑 / <6 빨강, ConsensusBadge(high/medium/low) `useQuery` retry 1. (12) `components/run/FinalHtmlPreview.tsx` — iframe sandbox `allow-scripts allow-same-origin` (CHECKLIST/CALCULATOR script 동작 필수), "새 창에서 열기" 버튼, 파일 크기 표기, NotAvailable fallback. (13) `components/run/BottomTabs.tsx` — Tab 액티브 시 LG U+ pink 하단 라인 + bg 변화. (14) `app/run/[id]/page.tsx` 상단 3-컬럼 (B3-S3-C 그대로 회귀 0) 높이 `h-[70vh]` 제한 + 하단 `<BottomTabs defaultTab="judge">` 추가. **frontend dep**: `recharts` 신규 설치 (36 pkg added). **`npm run build` PASS**: 6/6 prerender, /run/[id] 109 kB, 타입 에러 0. **임시 디버그 흔적 잔존 없음**. **CLI vs API final_output.html 동일성**: wrapper literal 100% 일치 (구조 보장, 신규 API run 1회 실측은 사용자 깨어난 후 권장). 잔여: §12 사용자 수동 검증 (브라우저). | B3-S3-D 명세 §18 종료 조건 95% 충족. /admin/prompts 편집기는 cut 결정 유지. |
| 2026-06-05 | **Railway 백엔드 배포 완료** — `Procfile` 단일 워커 `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`, `.python-version=3.11`, `railway.json` healthcheck=`/api/health`. 운영 실측: `/api/health` 200 + `judge_panel_available=true`, SSE 버퍼링 없음, 9 에이전트 풀 파이프라인 완주(`2026-06-05T00-50-24_c98b5ddc` 319초 weighted=67.2 failed_models=[]), iframe 서빙 OK. | 발표 시 라이브 데모 가능 환경 확보. 배포 운영 = 동일 코드가 Vercel + Railway 양방향 자동 재배포. |
| 2026-06-05 | **Vercel 프론트 배포 + CORS 연동** — GitHub repo `uplusaisearch-cyber/aiden` 연결, push → 자동 재배포. 백엔드 `API_CORS_ORIGINS` env 에 Vercel origin 추가하여 EventSource SSE 가 cross-origin 으로도 동작. | 프론트는 push 만으로 운영 반영 자동화. CORS 누락이 EventSource silent fail 의 직접 원인이므로 명시 설정 필수. |
| 2026-06-05 | **final-html iframe 404 fix** — 배포 컨테이너 기동 시 `runs/` 디렉터리 부재 → FastAPI 의 `/runs` StaticFiles mount 가 startup 에서 스킵 → iframe 이 `/runs/{id}/final_output.html` 직접 접근 시 404. `judges.py:35` 의 메타 url 을 `/api/runs/{id}/output` 으로 일원화하고 StaticFiles mount 자체 제거. API 경로는 ondemand 디스크 read 라 startup 시 디렉터리 존재 여부 무관. | 배포 환경 휘발성 파일시스템과 startup 검증 사이의 함정 1건 해소. (해당 함정은 v2 에서 admin ephemeral 폴더 안내 메시지의 근거가 됨) |
| 2026-06-05 | **B3-S3-E admin 콘솔 완료**: 명세 `docs/patches/2026-06-04_b3-s3-e_admin_persona_ops.md`. **A1 prompts.py 보강** — 기존 `/api/prompts` 12개 GET/PUT 위에 `GET /history`·`POST /restore`·`POST /rollback` 3 endpoint + `_defaults/` 부팅 스냅샷 + display_name/emoji/color_key 메타. 신규 라우터 만들지 않고 보강(중복 회피). **A2 RuntimeKeyStore** — 프로세스 메모리 dict 싱글톤, threading.Lock 직렬화, `runtime > env` 순. LLM 호출 6개 지점(`llm_clients._call_gemini/_openai/_anthropic` + `openai_client.call_openai_judge` + `anthropic_client.call_anthropic_judge` + `judge_panel._call_gemini_judge_default`)에서 `settings.X_api_key` → `get_provider_key(p) or settings.X_api_key` 로 wrap. **클라이언트 초기화 인자(grounding/JSON mode) 무변경** → healthcheck `judge_panel_available=true` 유지. 응답·로그 평문 키 누출 0. **A3 topic_registry** — `data/topic_registry.json` CRUD + `{{PUBLISHED_TOPICS}}` placeholder 를 Topic Scout(01) 에 추가, `concrete_agents.make_agent_callable(dynamic_vars_fn=_scout_dynamic_vars)` 로 매 호출 시점에 published+미만료 토픽을 동적 주입. 다른 8개 에이전트 호출 경로 무변경. 빈/없음/깨진 JSON 4 케이스 모두 안전 폴백 (`(이미 발행된 토픽 없음)`). **프론트 5 페이지** — `/admin/{,personas,keys,registry,settings}` + AdminSidebar + ToastStack + admin-api.ts. Persona Lab 은 **Monaco Editor**(`@monaco-editor/react@4.7.0` + `monaco-editor@0.55.1`, `next/dynamic(ssr:false)` 로 SSR-safe, `aiden-dark` 커스텀 테마로 디자인 토큰 매칭). **회귀**: backend pytest **56/56 PASS**, `npm run build` 6/6 prerender, 운영 라우터 3개 GET 200 검증 (`/api/prompts`=12, `/api/admin/keys`=3 마스킹, `/api/admin/registry`=0). 운영 + 로컬 라이브 generate 완주 재검증 (status=completed). | B3-S3-E (어드민 운영 콘솔) 종료. Persona Lab 가 9+3 에이전트 system prompt 를 코드 수정·재배포 없이 실시간 튜닝 + 롤백 가능 + 발행 토픽 중복 회피까지 자동화. **전 admin 기능 ephemeral** (재배포 시 초기화, v2 에서 Volume/DB 영속화). |
| 2026-06-04 | **B3-S3-C 라이브 검증 + 인프라 견고화 (3 commits)**. **commit 1 (`4332407` fix(sse))**: 라이브 화면 멈춤/30초 끊김의 **3개 root cause** 종합 fix. (a) backend `asyncio.wait_for(sub.__anext__(), timeout=HEARTBEAT_SEC)` 가 async generator 를 cancel → 매 30초 stream 종료 → `broker.subscribe(heartbeat_sec=)` 옵션 추가, generator 내부 timeout 처리 (b) CORS `allow_origins` 에 `127.0.0.1:*` 누락 → default 추가 + `allow_credentials=True` (c) frontend `useRunStream::appendUnique` 가 outer `seenIds: Set` 을 mutate → **React Strict Mode 가 setState updater 를 2회 호출**, 두번째에서 이미 add 된 id 가 dedup → messages 빈 배열로 reset → 화면 영원히 "연결중...". updater 안에서 prev 기반 Set 재생성 (pure). 진단 흐름 1차 가설(listener mismatch)·2차(CORS+30초)·3차(Strict Mode) 모두 `docs/issues/2026-05-25_open_issues.md` 의 closed 이슈 3건에 자세히 기록. + SSE buffer/replay 도 같이 (publish-before-subscribe / 재연결 손실 방어, ring `deque(maxlen=500)` + 30분 TTL). 신규 테스트 `test_sse_buffer.py` 6건. **commit 2 (`87653d2` feat(llm))**: Gemini 503/429/빈응답 자동 폴백. 모델 체인 `gemini-2.5-flash → gemini-2.5-flash-lite` (env `AIDEN_GEMINI_MODELS` override 가능), exponential backoff (1s→2s→4s→8s ±30% jitter, 모델당 3회), `_NO_GROUNDING_MODELS` 자동 강등(lite 는 grounding off + JSON mode), **빈 응답을 `GeminiEmptyResponseError` 로 분리해 retryable 처리** — 기존엔 `_extract_text` 가 빈 string 반환 → ValueError 즉시 raise → 폴백조차 못 가던 fact_checker 케이스 해소. finish_reason/block_reason 진단 정보 포함. 4xx / JSON parse 실패는 즉시 실패. 신규 테스트 `test_gemini_fallback.py` 12건. **commit 3 (`2d7dfb1` feat(frontend))**: `app/error.tsx` + `app/not-found.tsx` 추가 → `npm run build` 가 `/404`,`/500` prerender 에서 `<Html> should not be imported outside of pages/_document` 로 실패하던 문제 해결, `/_not-found` 138B 정적 prerender, 6/6 PASS. 메인/run 페이지 에러 화면 스타일과 일관. **전체 backend 회귀 51/51 PASS** (기존 33 + SSE buffer 6 + Gemini 12). **사용자 라이브 검증 통과** — `/run/[id]` 시크릿 창에서 9 에이전트 채팅 라이브 도착. | B3-S3-D 진입 + production 배포 가능 상태. 잔여 별건: `#W-sse-pipeline-complete-reconnect` (native EventSource auto-reconnect 루프, useRunStream 안 깨지지만 백엔드 부하), fact_checker 라이브 환경 검증, `/api/personas` 에 judge 페르소나 추가 |
| 2026-06-05 | **Judge Panel 역할 재정의** — "공모전 심사위원" → "플러스탭 콘텐츠 품질 평가 위원" (`10/11/12_judge_*.md` 활성본 + `_defaults/` snapshot 동시 갱신). "발행 가능한 품질 수준인지 평가" 문장 추가. 평가 5축·가중치·통과 컷·산출식·outlier·JSON 출력 스키마 모두 무변경 — 역할 정의 텍스트 / "심사위원→평가 위원" 호칭만 손댐. commit 9ae0424. | "공모전" 표현이 운영 발행 검수 맥락과 어긋남 (1회성 출품 vs 발행 전 품질 게이트). _defaults 도 동시 갱신해야 admin "Restore" 시 옛 문구 복귀 방지. |
| 2026-06-05 | **9 에이전트 발화 고도화 (Part A: personas + prompts)** — `personas.yaml` prefix/suffix 풀 3→**8**개 확장, A-3 톤 가이드 차별화(scout=들뜬 발견자 / analyst=냉정한 분석가 / planner=큰 그림 디렉터 / writer=몰입한 창작자 / factchecker=깐깐한 의심가 / devils=삐딱한 반론자 / editor=균형 조율자 / architect=구조 설계자 / builder=손 빠른 구현자). humanizer md5-seed 결정성 유지(같은 raw_text → 같은 발화). 9개 에이전트 md 의 JSON 출력 텍스트 필드(`reasoning`/`angle`/`summary`/`rationale`/`critical_issues.problem`/`editorial_decision`/`format_analysis`/`type_reasoning` 등 — `trace_converter` 가 body_text 로 가져가는 필드)에 "구체 인용·고유명사·수치 명시, 2~4문장, 일반론 금지" 지시 추가. JSON 출력 스키마(키/필수필드) 무변경. commit fa7f1e1. | 발화는 agent 프롬프트가 아니라 `personas.yaml` + `trace_converter` 의 합성물(메커니즘 조사 결과). 따라서 옵션 풀 + 출력 텍스트 필드 양쪽을 같이 강화해야 채팅 UI 가 콘텐츠 디테일을 인용. 옵션 풀 expansion 은 hash 분포가 바뀌어 *과거 run replay* 의 발화 텍스트 미세하게 달라질 수 있음 (결정성 자체는 유지). |
| 2026-06-05 | **trace_converter 키 정합 + "까겠습니다" 하드코딩 제거** — `_convert_devils` 가 읽던 `critical_issues[0].issue` 는 실제 스키마 키가 `problem` (06_devils_advocate.md). `_convert_architect` 가 읽던 `rationale` 은 스키마에 없는 키 (실제는 `format_analysis`/`type_reasoning`). 두 함수 모두 옳은 키 우선 + 구버전 폴백 체인(`problem or issue` / `format_analysis or type_reasoning or rationale`)으로 교정. devils headline 의 동사구 `"{N}건 까겠습니다. 평균 {avg}"` 는 `"{N}건 비판. 평균 {avg}"` 로 중립화 — 비판 톤은 `personas.yaml` 의 suffix_options 가 담당하도록 위임. commit fa7f1e1. | converter ↔ prompt 스키마 불일치로 devils/architect 의 body_text 가 항상 빈 문자열이던 잠복 버그 해소. 본 패치로 B3-S3-F 에이전트 상세 모달의 전용 렌더러가 실제 데이터를 노출할 수 있게 됨 (devils의 critical_issues, architect의 format_analysis). 33 unit tests PASS (issue fallback 으로 기존 test_6_devils_pass_branch 하위호환 유지). |
| 2026-06-05 | **Part B 콘텐츠 품질 패치 (출처 필터 + Judge 5축 앵커)** — Writer md 에 "출처 채택·배제 규칙"(현재일 이후 미래 날짜 출처 배제, 익명/비특정 도메인 배제(아하·나무위키·개인 블로그 등), 공신력 소스 우선(언론사·공공기관·통계·공식 채널)). Fact-Checker md 에 "출처 위반 강제 적시"(미래 날짜·익명 도메인 → unverified, 사실 오류 → corrected + correction 필드, summary 에 `[출처 위반]` / `[사실 오류]` 형식 명시, **검증 로직 무약화** 명문화). Judge 3개 (`10/11/12`) 에 5축 정성 앵커(`발행 가능 / 주의 / 재작성 필요` 3단계, "70 컷" 같은 수치 표현 미사용). 가중치·산출식·outlier·JSON 출력 스키마 **무변경**. commit fa7f1e1. | 운영 weighted_total 67.2 원인 진단 결과 "콘텐츠가 실제로 약함"(미래 날짜 출처·비공신력 도메인) 우세 → 옵션 B-2 A+B 채택(생성측 + 평가 캘리브레이션). 가중치/컷 조정(C)은 점수 인플레·셀링포인트 훼손 우려로 보류, Judge gating 자체도 현재 코드 미구현이라 별건 안건. |
| 2026-06-05 | **B3-S3-F 에이전트 상세 모달 (프론트 전용)** — 트레이스 버블 클릭 → 모달, 같은 `agent_id` 의 iter별 메시지를 Base UI `Dialog` + `Tabs` 로 묶음. Writer(본문 word-diff 좌/우 컬럼, LCS 백트래킹 자체 구현 `lib/wordDiff.ts`) / Fact-Checker(verified·unverified·corrected 색구분 카드) / Devils(문제→제안 쌍 카드 + scores 5축 그리드) / Editor(accepted·rejected 2열 + revision_instructions) 전용 렌더러 4종 + 나머지 5종(scout/analyst/planner/architect/builder) `GenericDetail` 공통 카드(중첩 객체 `<details>` 접힘). Judge 버블 미적용(B3-S3-D 별도 시각화 담당). 기존 디자인 토큰·`@base-ui/react` (이미 설치) 사용 — 신규 의존성 0. `ChatStream.tsx` 의 `<pre>` 펼침 제거 + `selectedAgentId` state + 같은 agentId messages 필터. commit 402dfaf (10 files, +1198/-13). | trace_converter 가 raw_json 으로 step output 전체를 ChatMessage 에 실어주는 구조라 추가 API 없이 모달이 데이터 그대로 활용. 발표 시 "Writer가 v1→v3로 글을 어떻게 고쳤나"·"Fact-Checker가 무엇을 걸렀나" 한눈에 보임. type-check + `npm run build` PASS. |
| 2026-06-05 | **`global-error.tsx` 최후 경계 추가** — `app/global-error.tsx` 신규. 인라인 minimal style(`#0a0a0b`/`#f4f4f5`/system-ui), 자체 `<html lang="ko"><body>`. props 시그니처에서 `reset` 미수신 — global 상황은 layout 자체가 회복 불가일 수 있어 `window.location.reload()` 가 안전. 새로고침 버튼 1개에만 브랜드 핑크(`#ff2e98`) 액센트. `error.tsx`/`not-found.tsx` 는 commit 2d7dfb1 구현이 이미 명세 요구사항 충족 → 무변경 유지. commit 3c1e5d0. | layout/Providers 자체 죽었을 때의 safety net. 마감 6/8 발표 시 "백색 깨진 페이지" 보이는 최악 케이스 방어. 자체 html/body 라 글로벌 토큰·다크 테마·Pretendard 못 받지만 인라인 색·폰트로 사용자 경험 보호 우선. |
| 2026-06-05 | **폴리싱 2차 run UI 3건 완료** — (1) `PlaybackToggle` 컴포넌트 삭제 + `page.tsx` import/사용처 제거 (no-op + "재생" 단어 오독 소지 해결, replay 실 동작은 별건 v2). (2) 정상 라우트 ← 메인을 가운데 헤더 우측 → 풀폭 슬림 top bar 좌상단으로 이동, 가운데 헤더는 `justify-between` → 좌측 단일 정렬로 정리. 에러/폴백 ← 메인 4곳(`run/[id]:64,99` / `error.tsx:46` / `not-found.tsx:20`) 무변경. (3) `personas.yaml` `stages.gameifier.display_name` "Game-ifier" → "인터랙티브 빌더" 1줄. internal key `gameifier` 불변(5개 변경점 회피). 백엔드 docstring/log 의 `Game-ifier` 잔재는 비-display 라 유지. 명세 `docs/patches/2026-06-05_run-ui-cleanup.md`. `npm run build` PASS. commit fa08969(코드 4 files +13/-88) + 1c08389(명세 추가). | 라이브 UI/SSE/그리드/다크모드/회귀 0. 디자인 토큰·shadcn·브랜드 핑크 그대로. 신규 디자인 없음. |
| 2026-06-05 | **토큰·비용 실측을 run 결과물에 종속 저장 (rev2 B-안전 방안)** — 라이브 표시는 *아예 포기*. `cost_tracker._runs[run_id]` 에 `prompt_tokens`/`completion_tokens` 필드, `record()` 시그니처에 토큰 keyword 인자(default 0). `llm_clients.py:338` 가 SDK 실측 토큰(`p_tok`/`c_tok`)을 함께 누적. `trace_logger.write_metadata(cost_summary=)` 인자 추가 → `metadata["cost"]` 에 `{newsroom: {is_actual_tokens: true, ...}, judge: {is_actual_tokens: false, note: "..."}, total: {...}}` breakdown 저장. judge 토큰은 `judge_panel._TOKEN_ESTIMATE` 호출당 2000/1000 고정 추정(실측 잡으려면 별도 3 함수 패치 필요 — 별건). `RunDetail.cost` 신규 필드로 API 노출, `routers/runs.py` 가 `metadata["cost"]` 끌어올림. **NowPlayingPanel UsageCard 제거**(4→3 카드). **SSE 보호 최우선** — `stream.py`/`useRunStream.ts`/`sse_broker.py` diff 0, `onCostUpdate` 리스너 + `totalTokens`/`totalCostUSD` state 필드는 회귀 위험 회피 위해 dead 데이터로 의도 유지. backend pytest 49 PASS, npm build PASS. commit ffe450a (8 files, +238/-31). | 진단 결과 라이브 UI 비용은 dead listener (`cost_update` 미발행) 라 항상 0이고, 종료 후엔 judge_panel 추정치만 표시되던 문제. 해결: 라이브 분기를 손대지 않고(SSE 회귀 표면 0) run 결과물에만 종속 저장 → 표시는 별도 히스토리 DB 작업이 가져감. **단가 placeholder(gpt-5 / claude-opus-4-7) 잔존** — 실시세 미확인, 본 작업에서 덮어쓰지 않음. |

---

## ⚠️ 이슈 / 리스크

> 발견 시 `발견일 · 항목 · 영향도(낮음/중간/높음) · 대응안` 형식으로 추가.

- **HTML Builder placeholder 주석 내부 치환 위험 (해결책 확정)** — base_agent 치환을 Format Architect 의 `placeholder_locations` 화이트리스트 기반으로 구현하기로 결정. 매핑 외 `{{VAR}}` 는 무시. 묶음 2 base_agent.py 구현 시 적용. 상세는 `docs/NEXT_BUNDLE_NOTES.md` §6.
- **2026-05-25 · gemini_client.py 가 deprecated 라이브러리(`google-generativeai`)·deprecated 모델(`gemini-2.0-flash`) 사용 · 영향도 높음 · ✅ 해소(2026-05-25 재시도)** — Step 2.5 첫 시도 시 Trend Scout 호출 자체 실패. `google-genai 2.6.0` + `gemini-2.5-flash` 마이그레이션으로 모든 P0 해소. Topic·Content Newsroom 실제 동작 확인. 상세는 `docs/early_integration_report.md` 재시도 섹션.
- **2026-05-25 · FC iter 3 verification_log 비어있음 · 영향도 낮음(P2 관찰)** — Step 2.5 재시도 실측: Writer iter 3 출력에 fact_claims 없거나 FC 가 검증할 게 없다고 판단. confidence=10/verified=0/0. 차단 아님(이미 approved 도달). Writer prompt 에 "iter N+ 에서도 fact_claims 유지" 점검 필요. 별도 검토.
- **2026-05-25 · 묶음 3 Step 1 완료 시점 신규 누적 이슈 4건 (#W-fc-empty, #docs-path-mismatch, #windows-tmp-path, #da-iter3-regression) · 영향도 혼합** — 상세는 `docs/issues/2026-05-25_open_issues.md` 참조.
- **2026-06-04 · B3-S3-C 라이브 검증 종합 fix · 영향도 높음 · ✅ 해소(2026-06-04, commits 4332407 · 87653d2 · 2d7dfb1)** — 라이브 SSE 30초 끊김 + 화면 멈춤(Strict Mode impure updater) + Gemini 503/빈응답 폴백 부재 + production build prerender 실패 4건 종합 해소. closed 이슈 3건(#W-sse-cors-blocked, #W-sse-30s-disconnect, #W-usestream-impure-updater) 진단 흐름 `docs/issues/2026-05-25_open_issues.md` 에 기록.
- **2026-06-04 · #W-sse-pipeline-complete-reconnect · 영향도 낮음 · 미해소** — `pipeline_complete` 후 백엔드 `broker.close()` → buffer 30분 TTL 남김 → native EventSource 가 connection 종료 감지 → **자동 reconnect** → buffer 전체 replay 후 또 close → 무한 루프. `useRunStream` 은 `pipeline_complete` 리스너 안에서 `es.close()` 호출하므로 안 깨지지만, 직접 EventSource 사용 시나리오(진단 콘솔 등) 에서 백엔드 부하 우려. 별건 commit 으로 처리 예정 (예: subscribe `already_closed` 분기에서 SSE 응답 `retry: -1` 헤더 추가하거나 close sentinel 을 buffer 끝에 두기).
- **2026-06-05 · final-html iframe 404 (배포) · 영향도 높음 · ✅ 해소** — 컨테이너 기동 시 runs/ 부재로 /runs StaticFiles mount 스킵 → 메타 url 을 /api/runs/{id}/output 으로 일원화. judges.py:35.
- **2026-06-05 · Gemini 빌링 prepay credits 소진 · 영향도 높음 · ✅ 해소** — 운영 + 로컬 모두 Trend Scout 17초 대기 후 `429 RESOURCE_EXHAUSTED: Your prepayment credits are depleted` 로 stage 1 fail. 사용자 AI Studio 충전 후 propagation 완료 → 운영 환경 `2026-06-05T00-50-24_c98b5ddc` 9 에이전트 완주(319초, weighted=67.2). 진단: trace `agents/01_trend_scout.json` 의 raw error 메시지가 결정타였음.
- **2026-06-05 · 누적 사용량 토큰 0 표시 · 영향도 낮음 · 미해소(구조적)** — cost_tracker 에 token 필드 자체 부재. UI 표시는 항상 0. 비용 추적은 정상 동작하지만 토큰 카운트는 명시적으로 미구현. 마감 후 후보, 데모 비차단.
- **2026-06-05 · 콘텐츠 출처 품질 (미래 날짜·비공신력 출처) · 영향도 중간 · 부분 해소** — Trend Scout/Fact-Checker 출처가 가끔 미래 날짜(target_date 캐리오버 오해)나 비공신력 사이트 인용. 운영 weighted_total 67.2 (improving). 추가 필터링(도메인 화이트리스트·날짜 sanity check) 후보. 마감 후 우선순위.
- **2026-06-05 · 전 admin 기능 ephemeral · 영향도 중간 · 의도된 동작** — Persona Lab 프롬프트(`_defaults/`, `.versions/`), 런타임 API 키(메모리), 발행 토픽 레지스트리(`data/topic_registry.json`) 모두 Railway 재배포 시 초기화. UI 안내 배너 + RESULT.md 명시. v2 에서 Volume/DB 영속화 예정.
- **#W-sse-pipeline-complete-reconnect (2026-06-04) · 영향도 낮음 · 브라우저 실 발현 여부 미확인** — `useRunStream` 은 `pipeline_complete` 안에서 `es.close()` 호출하므로 안 깨지나, native EventSource 직접 사용 시나리오에서 재연결 루프 가능. 데모 비차단 가설 단계. 모니터링.
- **2026-06-05 · API 경로 `final_output.html` 저장 누락 (의심) · 영향도 중간 · 미해소** — 특정 조건(상태=degraded 또는 `result.final_html` 부재)에서 `run_manager._run_pipeline:191-201` 의 저장이 스킵될 가능성 있음. 사용자 보고 기준. 재현 로그 확보 후 패치. 마감 후.
- **2026-06-05 · Fact-Checker 빈 응답(safety / grounding+json 충돌 의심) · 영향도 중간 · 미해소** — 운영에서 Fact-Checker 가 가끔 빈 응답. Gemini grounding + JSON mode 조합의 safety filter 또는 응답 길이 cutoff 의심. 별건 진단 필요. 마감 후.
- **2026-06-05 · 고아 run 회수 메커니즘 없음 · 영향도 중간 · 미해소** — `RunManager._active[sid]` 의 task 가 SSE 연결 끊김에도 cancel 되지 않음(`run_manager.py:71, 92-94`, `stream.py:73-81`). 사용자 이탈 후 `PIPELINE_TIMEOUT_SEC=20*60`(20분) 까지 계속 회전하며 LLM 비용 누적. 회수 패치는 별건: SSE last-seen 추적 + N초 무구독 시 `task.cancel()` 추가. 마감 후 우선순위.
- **2026-06-05 · Railway 재기동 시 in-flight run 소실 · 영향도 중간 · 의도된 동작 (인-프로세스 dict)** — `_active` 가 프로세스 메모리 dict 이므로 healthcheck 실패·재배포로 process kill 시 active run 전부 사라짐. 외부 큐(Redis/RQ/Celery) 도입은 v2 범위.
- **2026-06-05 · Judge 통과 컷 70 게이팅 미구현 · 영향도 낮음 · 의도된 상태** — `weighted_total` (10-100) 표시만, gating 로직 부재(코드/설정 어디에도 70 컷 없음, `judge_panel.py:197-199` weighted_total 산출만). 발행 자동화 도입 시 신설 안건. 본 패치 5축 정성 앵커도 "수치 컷" 미언급으로 일관.
- **2026-06-05 · `_defaults/` 미동기화 (발화·앵커 패치분) · 영향도 낮음 · 미해소** — Judge 역할 재정의(9ae0424)는 `_defaults/` 동시 갱신했으나 발화·앵커 패치(fa7f1e1)는 활성본만 변경. 어드민 "Restore" 누르면 옛 문구 복귀. `_defaults` 는 `backend/api/routers/prompts.py:128-144` 의 부팅 시 1회 스냅샷 방식이라 이미 배포된 인스턴스 자동 동기화 안 됨. 마감 후 별건 패치.
- **2026-06-05 · 단가 placeholder 잔존(gpt-5/claude-opus-4-7) · 영향도 낮음 · 미해소** — `llm_clients.py:97-98` 의 `_PRICE_TABLE` 과 `judge_panel.py:37-38` 의 `_JUDGE_PRICE_TABLE` 에 동일 placeholder 단가(gpt-5: 5.00/15.00, claude-opus-4-7: 15.00/75.00). `# placeholder` 주석 명시. 실시세 확인 후 교정 필요(두 출처 동기화). 본 작업(ffe450a)에서 덮어쓰지 않고 보존.
- **2026-06-05 · cost_tracker `_runs` 메모리 누수 가능 · 영향도 낮음 · 미해소** — `reset_run(run_id)` 정의됐으나 호출처 0건 (grep). 장수명 프로세스에서 run 끝나도 `_runs` dict 에 누적. 마감 후 별건: `run_manager._execute` 의 finally 에 `tracker.reset_run(session_id)` 추가로 처리.
- **2026-06-05 · Judge Panel 토큰 실측 미확보 · 영향도 낮음 · 의도된 상태** — newsroom 9 에이전트는 SDK usage 실측, judge_panel 3 함수는 `_TOKEN_ESTIMATE` 호출당 input=2000/output=1000 고정 추정 사용. `metadata.cost.judge.is_actual_tokens=false` + note 명시로 구분. Judge 실측 잡으려면 `_call_gemini_judge_default` / `openai_client.call_openai_judge` / `anthropic_client.call_anthropic_judge` 3 함수에 SDK usage 추출 + `tracker.record` 호출 추가 필요. 마감 후.
- **2026-06-05 · UI 폴리싱 2차 잔여 3건 · 영향도 낮음 · ✅ 해소(2026-06-05, commit fa08969)** — (a) `PlaybackToggle` 컴포넌트 삭제 — no-op + "재생" 오독 소지 동시 제거. replay 실 동작은 별건 v2 큐. (b) ← 메인을 풀폭 슬림 top bar 좌상단으로 이동, 가운데 헤더는 좌측 단일 정렬로 정리. (c) `personas.yaml` 의 `gameifier.display_name` 1줄 변경 → "인터랙티브 빌더". internal key 불변.

---

## 🎯 다음 추천 액션 (마감 **2026-06-08** 까지)

**우선순위 1 — 발표/결선 PT 자료 (별도 채팅 권장).** 본 채팅 context 가 무거우므로 새 세션에서 다음 자료를 가져가면 됩니다:

1. 운영 라이브 URL (Vercel) + 운영 run (`2026-06-05T00-50-24_c98b5ddc`, weighted=67.2)
2. 메타 산출물 폴더 (`runs/2026-05-25T06-16-20_1bc88d21/` 9 에이전트 첫 완주 trace + final_output.html)
3. 아키텍처 다이어그램 초안 (3 Newsroom + Judge Panel + admin 콘솔 + 에이전트 상세 모달)
4. 본 PROGRESS.md 의 의사결정 로그 30+ 건 — 디자인 결정의 "왜" 모두 포함
5. B3-S3-E RESULT.md (`docs/patches/2026-06-04_b3-s3-e_RESULT.md`)
6. **신규**: B3-S3-F 에이전트 상세 모달 + 발화 고도화 + Judge 앵커 (commits `fa7f1e1`, `402dfaf`)

**우선순위 2 — 운영 종단 회귀.**
- 운영 환경에 신규 commit (`9ae0424` Judge 역할 / `fa7f1e1` 발화·콘텐츠 품질 / `402dfaf` 에이전트 모달 / `3c1e5d0` global-error / `ffe450a` 토큰·비용 실측 / `fa08969` run UI 폴리싱 2차) 반영 후 1 run 회귀
- 종단 검증 포인트: 발화 다양성 / 모달 동작 / Judge 5축 앵커 효과 / `runs/<sid>/metadata.json` 의 `cost` 섹션 + `GET /api/runs/<sid>` 의 `cost` 필드 노출 / 좌상단 ← 메인 + Game-ifier→"인터랙티브 빌더" 라벨 정상 표시

**우선순위 3 — 여유 시.**
- Format Architect 인터랙티브 요소 지시 강화 (C 타입 채택률 + 본문 부합도)

**마감 후 (별건 큐).**
- 단가 placeholder 교정(gpt-5/claude-opus-4-7 실시세, `_PRICE_TABLE`/`_JUDGE_PRICE_TABLE` 두 출처 동기화)
- Judge Panel 토큰 실측 (3 judge 함수 SDK usage 추출 + `tracker.record` 호출 추가)
- cost_tracker `reset_run` 호출 추가 (메모리 누수 방지)
- 고아 run 회수 (`task.cancel()` 트리거 신설)
- `_defaults/` 발화·앵커 동기화
- Judge 통과 컷 gating
- Fact-Checker 빈 응답 진단
- `final_output.html` 저장 누락 케이스 진단
- prompt 튜닝 사이클

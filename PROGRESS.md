# AIDEN 개발 진행률

> 이 문서는 **AIDEN 개발 과정 자체**의 공정률을 추적합니다.
> (AIDEN이 생성하는 콘텐츠나 운영 기능과는 별개)

| 항목 | 값 |
|---|---|
| **마지막 업데이트** | 2026-05-23 |
| **전체 진행률** | **63.0%** (29/46 항목 완료) |
| **현재 Phase** | Phase 2 진행 중 (묶음 2 Step 3-1 완료 / Topic Newsroom + 트레이스 로깅 기반) |

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

## Phase 2: 9 Agents + Orchestration ⬜

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
- [ ] Topic Newsroom 오케스트레이터 (Stage 1)
- [ ] Content Newsroom 오케스트레이터 (Stage 2, max 3 iter)
- [ ] Game-ifier 오케스트레이터 (Stage 3)
- [ ] Judge Panel 오케스트레이터 (Stage 4)
- [ ] 콘솔 end-to-end 통합 테스트

---

## Phase 3: API Server ⬜

- [ ] FastAPI 기본 서버 구조
- [ ] POST /api/generate 엔드포인트
- [ ] GET /api/stream/{job_id} SSE 엔드포인트
- [ ] 에이전트 trace 실시간 발행
- [ ] CORS 설정
- [ ] 에러 핸들링

---

## Phase 4: Frontend + Admin ⬜

- [ ] Next.js 14 프로젝트 셋업
- [ ] Tailwind + shadcn/ui 설정
- [ ] 메인 페이지: 카테고리 선택 UI (프리셋 4 + 자유 입력)
- [ ] 트레이스 대시보드 (에이전트별 색상 채팅 버블, SSE 연결)
- [ ] 최종 콘텐츠 미리보기 (iframe)
- [ ] 심사 결과 카드 3개
- [ ] 어드민: system prompt 편집기 (9개 .md 파일 웹에서 수정)

---

## Phase 5: Deploy + Polish ⬜

- [ ] Vercel 배포 (Frontend)
- [ ] Railway 배포 (Backend)
- [ ] 환경변수 설정
- [ ] 프리셋 4개 카테고리 라이브 테스트
- [ ] 프롬프트 튜닝 사이클
- [ ] 데모 시나리오 검증
- [ ] 발표 자료 작성
- [ ] 메타 산출물 정리 (아이데이션 트레이스, 아키텍처 다이어그램)

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

---

## ⚠️ 이슈 / 리스크

> 발견 시 `발견일 · 항목 · 영향도(낮음/중간/높음) · 대응안` 형식으로 추가.

- **HTML Builder placeholder 주석 내부 치환 위험 (해결책 확정)** — base_agent 치환을 Format Architect 의 `placeholder_locations` 화이트리스트 기반으로 구현하기로 결정. 매핑 외 `{{VAR}}` 는 무시. 묶음 2 base_agent.py 구현 시 적용. 상세는 `docs/NEXT_BUNDLE_NOTES.md` §6.

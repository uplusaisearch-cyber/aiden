# AIDEN 개발 진행률

> 이 문서는 **AIDEN 개발 과정 자체**의 공정률을 추적합니다.
> (AIDEN이 생성하는 콘텐츠나 운영 기능과는 별개)

| 항목 | 값 |
|---|---|
| **마지막 업데이트** | 2026-05-22 |
| **전체 진행률** | **34.8%** (16/46 항목 완료) |
| **현재 Phase** | Phase 2 진행 중 (묶음 1 / 콘텐츠 품질 라인 완료) |

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
- [ ] Trend Scout system prompt 작성
- [ ] Audience Analyst system prompt 작성
- [ ] Strategy Planner system prompt 작성
- [x] Writer system prompt 작성 _(2026-05-22)_
- [x] Fact-Checker system prompt 작성 _(2026-05-22)_
- [x] Devil's Advocate system prompt 작성 _(2026-05-22)_
- [x] Editor-in-Chief system prompt 작성 _(2026-05-22)_
- [x] Format Architect system prompt 작성 _(2026-05-22)_
- [ ] HTML Builder system prompt 작성
- [x] 플러스탭 HTML 샘플 분석 → templates/plustab_structure.md 채우기 _(2026-05-22)_
- [x] type_a.html, type_b.html 템플릿 완성 _(2026-05-22)_
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

---

## ⚠️ 이슈 / 리스크

> 발견 시 `발견일 · 항목 · 영향도(낮음/중간/높음) · 대응안` 형식으로 추가.

- **2026-05-22 · HTML Builder placeholder 주석 내부 치환 위험 · 중간**:
  `type_a.html` / `type_b.html` 헤더 주석에도 변수명 문서화 목적의 `{{VAR}}` 가 등장함.
  HTML Builder 구현 시 Format Architect 가 명시한 `placeholder_locations.render_zone == "outside_comment"` 인 위치만 치환하도록 강제 필요.
  대응안: 묶음 2 에서 09_html_builder.md 작성 시 명시 + base_agent 치환 로직에 안전장치 추가 (`docs/NEXT_BUNDLE_NOTES.md` §1 참조).

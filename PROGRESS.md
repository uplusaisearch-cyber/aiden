# AIDEN 개발 진행률

> 이 문서는 **AIDEN 개발 과정 자체**의 공정률을 추적합니다.
> (AIDEN이 생성하는 콘텐츠나 운영 기능과는 별개)

| 항목 | 값 |
|---|---|
| **마지막 업데이트** | 2026-05-22 |
| **전체 진행률** | **19.6%** (9/46 항목 완료) |
| **현재 Phase** | Phase 2 진행 중 (코어 인프라 1건 완료) |

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
- [ ] Writer system prompt 작성
- [ ] Fact-Checker system prompt 작성
- [ ] Devil's Advocate system prompt 작성
- [ ] Editor-in-Chief system prompt 작성
- [ ] Format Architect system prompt 작성
- [ ] HTML Builder system prompt 작성
- [ ] 플러스탭 HTML 샘플 분석 → templates/plustab_structure.md 채우기
- [ ] type_a.html, type_b.html 템플릿 완성
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

---

## ⚠️ 이슈 / 리스크

> 현재 비어 있음. 발견 시 `발견일 · 항목 · 영향도(낮음/중간/높음) · 대응안` 형식으로 추가.

_(없음)_

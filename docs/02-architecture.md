# 02. Architecture

## 한눈에 보기

```
              ┌─────────────────────────────────────────────┐
              │              Frontend (Next.js)             │
              │     기획자 UI / SSE 스트리밍 토론 뷰         │
              └────────────────────┬────────────────────────┘
                                   │ SSE
              ┌────────────────────▼────────────────────────┐
              │          Backend API (FastAPI)              │
              │   /api/generate  /api/stream  /api/health   │
              └────────────────────┬────────────────────────┘
                                   │
              ┌────────────────────▼────────────────────────┐
              │      Orchestrator: Content Newsroom         │
              │  (9 agents, 3 rounds of discussion)         │
              └────────────────────┬────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
 ┌─────────────┐          ┌─────────────┐            ┌─────────────┐
 │  Stage 1    │          │  Stage 2-3  │            │  Stage 4    │
 │  Research   │   ───►   │  Draft /    │   ───►     │  Format /   │
 │             │          │  Critique   │            │  Output     │
 └─────────────┘          └─────────────┘            └─────────────┘
   Trend Scout              Writer                    Format Architect
   Audience Analyst         Devil's Advocate          HTML Builder
   Strategy Planner         Fact-Checker
                            Editor-in-Chief
```

---

## Stage 흐름

| Stage | 이름 | 참여 에이전트 | 목적 |
|---|---|---|---|
| 1 | Research | Trend Scout, Audience Analyst, Strategy Planner | 주제 리서치 + 타겟 분석 + 전략 수립 |
| 2 | Draft | Writer | 본문 초안 작성 |
| 3 | Critique | Fact-Checker, Devil's Advocate, Editor-in-Chief | 사실 검증 + 비판 + 편집 (최대 3 라운드) |
| 4 | Output | Format Architect, HTML Builder | 콘텐츠 타입 결정 + 최종 HTML 생성 |

---

## 9 에이전트 역할 요약

| # | 에이전트 | 모델 | Grounding | 역할 |
|---|---|---|---|---|
| 1 | **Trend Scout** | gemini_flash | ✅ | 최신 트렌드/뉴스 리서치 |
| 2 | **Audience Analyst** | gemini_flash | — | 타겟 독자 페르소나/니즈 분석 |
| 3 | **Strategy Planner** | gemini_pro | — | 콘텐츠 앵글/메시지 전략 수립 |
| 4 | **Writer** | gemini_pro | — | 본문 초안 작성 |
| 5 | **Fact-Checker** | gemini_flash | ✅ | 사실 검증 (출처 확인) |
| 6 | **Devil's Advocate** | gemini_flash | — | 비판/반박 (라운드별 5→3→1개) |
| 7 | **Editor-in-Chief** | gemini_pro | — | 최종 편집 판단 |
| 8 | **Format Architect** | gemini_pro | — | A/B/C 타입 및 인터랙티브 템플릿 선택 |
| 9 | **HTML Builder** | gemini_pro | — | 플러스탭 구조 준수 HTML 생성 |

> 모델 및 라운드 수는 `config/agents.yaml` 에서 코드 수정 없이 변경 가능합니다.

---

## 폴더 매핑

| 책임 | 위치 |
|---|---|
| 환경변수 로드 | `backend/core/settings.py` |
| LLM 통합 호출 | `backend/core/llm_clients.py` |
| Agent 베이스 클래스 | `backend/core/base_agent.py` |
| 9개 에이전트 인스턴스 | `backend/agents/definitions.py` |
| 시스템 프롬프트 | `backend/agents/prompts/*.md` |
| 뉴스룸 토론 진행 | `backend/orchestration/` (Phase 3) |
| HTML 템플릿 | `backend/templates/` |
| FastAPI 라우터 | `backend/api/` (Phase 3) |
| 브랜드/플랫폼 설정 | `config/brand.yaml`, `config/platform.yaml` |
| 에이전트 설정 | `config/agents.yaml` |

---

## 설계 결정 (Why)

- **system prompt 를 별도 .md 로 분리한 이유**:
  비개발자(기획/콘텐츠 담당자)가 코드를 만지지 않고도 에이전트 톤/지시를 튜닝할 수 있어야 함.

- **모든 설정을 YAML 로 빼낸 이유**:
  다른 브랜드/팀으로 이관 시 YAML 만 교체하면 즉시 사용 가능.

- **LLM 호출을 `llm_clients.py` 단일 모듈로 집약한 이유**:
  provider 교체/재시도/비용 추정/로깅을 한 곳에서 일관되게 처리.

- **JSON 응답 강제 (`response_mime_type="application/json"`)**:
  에이전트 간 데이터 교환을 안정화 (자유 텍스트는 파싱 실패 위험).

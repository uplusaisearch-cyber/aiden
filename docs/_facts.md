# AIDEN Facts Base (자동 추출)

> 추출 시점: 2026-06-07
> 추출자: Claude Code (Opus 4.7 1M)
> 명세: docs/patches/2026-06-07_facts-extraction.md
> 원칙: 코드 기반 사실만. 추측·미화 없음. 근거 위치 병기. 미확인 = `[확인 불가]`, 추정 = `[추정]`.
> 산출 범위: F1~F8 + 부록. `docs/_facts.md` 단일 파일.

---

## F1. 9개 에이전트

근거 단일 출처:
- `config/agents.yaml` (모델 별칭 ↔ 실모델 ID 매핑 + agent별 alias 매핑)
- `backend/agents/concrete_agents.py::_AGENT_SPECS` (short_key ↔ prompt 파일 ↔ yaml_agent_key)
- `backend/config/personas.yaml::stages` (Stage 소속)
- `backend/agents/prompts/*.md` (system prompt 본문)

### 별칭 → 실모델 ID 매핑 (`config/agents.yaml::models`)

| 별칭 | 실제 model_id |
|---|---|
| `gemini_pro_hi` | `gemini-3.1-pro-preview` |
| `gemini_pro` | `gemini-2.5-pro` |
| `gemini_flash` | `gemini-2.5-flash` |
| `anthropic_sonnet` | `claude-sonnet-4-6` |
| `anthropic_opus` | `claude-opus-4-7` |
| `anthropic_judge` | `claude-opus-4-7` |
| `openai_judge` | `gpt-5` |

### 9 에이전트 표 (stage 순)

| # | 에이전트 (한/영) | Stage | 별칭 | 실모델 ID | Grounding | 입력 | 출력 키 (대표) | 프롬프트 핵심 역할 |
|---|---|---|---|---|---|---|---|---|
| 1 | 트렌드 정찰 / Trend Scout (`scout`) | Topic Newsroom | `gemini_flash` | `gemini-2.5-flash` | ✅ ON (`agents.yaml::agents.trend_scout.grounding=true`) | `{category, target_date}` + 동적 `{{PUBLISHED_TOPICS}}` | `trending_topics`, `summary`, `search_queries_used` | Google Search Grounding 으로 카테고리 핫이슈 후보 추출. 발행 토픽 회피. |
| 2 | 독자 분석 / Audience Analyst (`analyst`) | Topic Newsroom | `gemini_flash` | `gemini-2.5-flash` | ❌ OFF | `{category, trending_topics}` | `audience_evaluation` | 토픽별 페르소나 적합도(fit_score) 평가. |
| 3 | 편집 기획 / Strategy Planner (`planner`) | Topic Newsroom | `gemini_pro_hi` | `gemini-3.1-pro-preview` | ❌ OFF | 위 두 출력 + 동적 `INJECTED_ANGLE/_DIRECTIVE/_SEGMENT/_SEGMENT_PERSONA` | `final_topic` | 최종 토픽 + 앵글 + 타겟 SEG 확정. |
| 4 | 집필 / Writer (`writer`) | Content Newsroom | `anthropic_sonnet` | `claude-sonnet-4-6` | ❌ OFF (Anthropic 미지원) | iter1: `{category, strategy}` / iter2+: `+previous_draft, factcheck_log, critique, editor_instructions` | `sections`, `title`, `intro`, `closing`, `cta` | 초안 작성 + 라운드별 재작성. 2026-06-06 Gemini → Claude Sonnet 교체. |
| 5 | 팩트 검증 / Fact-Checker (`fact_checker`) | Content Newsroom | `gemini_flash` | `gemini-2.5-flash` | ✅ ON (`agents.yaml::agents.fact_checker.grounding=true`) | Writer 출력 | `annotated_draft`, `confidence_score` | 인용/수치/도메인 grounding 으로 검증, 인라인 주석. |
| 6 | 반론 제기 / Devil's Advocate (`devils_advocate`) | Content Newsroom | `gemini_flash` | `gemini-2.5-flash` | ❌ OFF | annotated_draft + 이전 비판/Editor 응답 | `critical_issues` | 라운드별 가중치(5/3/1)만큼 critical_issues 제기. |
| 7 | 편집국장 / Editor in Chief (`editor`) | Content Newsroom | `anthropic_opus` | `claude-opus-4-7` | ❌ OFF (Anthropic 미지원) | Writer/Factcheck/DA 종합 | `decision`(approved\|needs_revision), `final_content`, `accepted/rejected_critiques`, `revision_instructions` | 통과/재작성/직접편집 결정. iter 3 강제 승인 책임. 2026-06-06 Gemini Pro Hi → Claude Opus 교체. |
| 8 | 포맷 설계 / Format Architect (`format_architect`) | Gameifier (UI 라벨: "인터랙티브 빌더") | `gemini_pro` | `gemini-2.5-pro` | ❌ OFF | `final_content` | `selected_type`(A/B/C), `placeholder_locations` 등 | A/B/C + 인터랙티브 위젯 후보 선택. |
| 9 | 퍼블리싱 / HTML Builder (`html_builder`) | Gameifier | `gemini_pro` | `gemini-2.5-pro` | ❌ OFF | `{final_content, format_decision}` | `html`, placeholder 치환 메타 | HTML 마크업 생성 + 화이트리스트 치환. |

코드 우선 원칙 검증:
- yaml `agents.writer.model = "anthropic_sonnet"` 가 코드 호출에서도 그대로 사용됨 — `concrete_agents.py::_build_agents` 가 alias 가 `anthropic_*` 시작이면 `AnthropicAgentClient` 로 라우팅 (`_build_client_for_alias` 분기).
- `agents.editor_in_chief.model = "anthropic_opus"` 동일 검증 OK.
- grounding 충돌 가드 (`concrete_agents.py:257-263`): `use_grounding=True` + `alias.startswith("anthropic")` 조합은 `gemini_flash` 로 강제 강등 + warning 로그. 현재 yaml 매핑상으로는 트리거되지 않음 (scout/fact_checker 는 `gemini_flash`).

### `gameifier` 내부 키 vs 노출 라벨

- 코드/디렉터리 키: `gameifier` (예: `backend/orchestrators/gameifier.py`, `personas.yaml::stages.gameifier`)
- 사용자 노출 라벨(personas.yaml `display_name`): **"인터랙티브 빌더"** + subtitle "인터랙티브 변환" + emoji 🎮
- 운영 문서·UI 트레이스 뷰어는 "인터랙티브 빌더" 표기 사용, 내부 코드는 `gameifier` 유지.

---

## F2. 파이프라인 구조 & 토론 루프

근거: `backend/orchestrators/full_pipeline.py`, `backend/orchestrators/content_newsroom.py`, `backend/api/services/run_manager.py`, `config/agents.yaml::orchestration`.

### 3-Stage 구성

| Stage | 클래스 | 입력 | 출력 | 흐름 |
|---|---|---|---|---|
| 1. Topic Newsroom | `TopicNewsroom` (`topic_newsroom.py`) | `category`, `target_date` | `final_topic` | 순차: Scout → Analyst → Planner. 각 단계 실패 시 `{error, partial}` 반환하고 종료. |
| 2. Content Newsroom | `ContentNewsroom` (`content_newsroom.py`) | `category`, `strategy=stage_1.final_topic` | `final_content`, `decision="approved"` 보장 | **루프** (최대 3 iter): Writer → Fact-Checker → Devil's Advocate → Editor. Editor 가 `approved` 면 즉시 종료, 아니면 다음 iter, iter 3 도달 시 강제 종료. |
| 3. Gameifier | `Gameifier` (`gameifier.py`) | `final_content` | `html`, `format_decision`, `html_meta` | 순차: Format Architect → HTML Builder. 둘 중 하나라도 실패하면 `_fallback_html` 로 plain HTML 폴백. |

선택 Stage 4 (Judge Panel) 는 §F3 참조. `FullPipeline.run()` 안 `if self.judge_panel and result.get("final_html"):` 조건 만족 시 호출.

### 토론 루프 파라미터 (Stage 2)

| 파라미터 | 값 | 근거 |
|---|---|---|
| `MAX_ITERATIONS` | **3** | `content_newsroom.py:23` + `config/agents.yaml::orchestration.content_newsroom.max_iterations=3` (값 일치) |
| Devil's Advocate 라운드별 critique 개수 | **iter1=5, iter2=3, iter3=1** | `config/agents.yaml::orchestration.content_newsroom.devils_advocate_critique_count` + `content_newsroom.py:24` `DA_CRITICAL_COUNT_BY_ITER = {1: 5, 2: 3, 3: 1}` 주석 "참고용 (prompt에 박혀있음)" → 실제 강제는 06_devils_advocate.md 프롬프트 |
| iter 3 강제 승인 + `known_weaknesses` 처리 | 있음 | `content_newsroom.py::_coerce_approved_at_iter3` (179-186, 337-378). Editor 가 iter 3 에서 `needs_revision` 반환 시 오케스트레이터가 `decision="approved"` 로 덮어쓰고 `known_weaknesses` 에 잔여 DA critique + Fact-Checker `confidence_score<=6` 사유 보강. |
| 추가 자가검증 | Editor self-edit 정합성 검사 | `_verify_editor_self_edits` (283-335): `accepted_critiques` 중 `action == "직접 수정함"` 항목이 있는데 sections 유사도(`difflib.SequenceMatcher.ratio()`) ≥ 0.99 면 `known_weaknesses` 에 경고 추가. |
| 실패 시 강제 승인 | 있음 | `_force_approve` (237-281): Writer/Fact-Checker/DA/Editor 중 하나라도 출력이 비면 partial 결과로 `decision="approved"` + `known_weaknesses` 채워서 반환. `_orchestrator_forced=True` 플래그. |

### SSE/파이프라인 실행 진입점

- HTTP 진입점: `POST /api/generate` → `backend/api/routers/generate.py::start_generate` → `RunManager.start_run` 즉시 `session_id` 반환 + 백그라운드 `asyncio.create_task` 로 `RunManager._execute` 가동.
- `_execute` → `_run_pipeline` (`run_manager.py:265-429`):
  1. `TraceLogger.new_run(...)` (SSE 브로커 + main_loop 주입)
  2. `PlanningSelector.instance().select(category)` 또는 `build_with_override(category, override)` 로 angle/segment 결정
  3. `build_all_agents(planning_selection=...)` 로 9 callable 빌드
  4. `JudgePanel.from_settings()` 시도 (`skip_judge` 옵션 없으면)
  5. `pipeline = FullPipeline(tracer, agents, judge_panel)` → `await asyncio.to_thread(pipeline.run, target_category_label)` (FullPipeline 은 sync)
  6. 완료 시 `final_output.html` 저장 + `outputs.db` upsert + `pipeline_complete` SSE 이벤트
- 타임아웃: `PIPELINE_TIMEOUT_SEC = 20 * 60` (1200초). 초과 시 `error` SSE 후 broker close.
- SSE 스트리밍: `TraceLogger.log_agent_step` 이 매 에이전트 단계마다 `sse_broker.publish` 호출 (run_manager.py 가 broker + loop 주입).

---

## F3. Judge Panel

근거: `backend/orchestrators/judge_panel.py`, `backend/core/judge_model_resolver.py`, `config/agents.yaml::judge_panel`, `backend/core/anthropic_client.py::call_anthropic_judge`, `backend/core/openai_client.py::call_openai_judge`, `backend/orchestrators/judge_panel.py::_call_gemini_judge_default`.

### 3개 심사 모델 (실제 모델 ID)

`config/agents.yaml::judge_panel.models` 기본값:

| Judge 이름 | 실제 model_id | 비동기 호출 함수 | 프롬프트 파일 |
|---|---|---|---|
| `gemini` | `gemini-2.5-pro` | `_call_gemini_judge_default` (`judge_panel.py:295-333`) | `backend/agents/prompts/10_judge_gemini.md` |
| `gpt` | `gpt-5` | `call_openai_judge` (`backend/core/openai_client.py`) | `11_judge_gpt.md` |
| `claude` | `claude-opus-4-7` | `call_anthropic_judge` (`backend/core/anthropic_client.py`) | `12_judge_claude.md` |

모델 해석 우선순위 (`backend/core/judge_model_resolver.py::resolve_judge_model`):
1. 어드민 UI 런타임 override (`runtime_override["gemini_model"]` 등)
2. 환경변수: `JUDGE_GEMINI_MODEL`, `JUDGE_GPT_MODEL`, `JUDGE_CLAUDE_MODEL`
3. `config/agents.yaml::judge_panel.models` 기본값

### 5축 평가 차원 (영문 키 ↔ 한국어 라벨)

- 영문 키 + 가중치 단일 출처: `config/agents.yaml::judge_panel.weights` (+ `validate_judge_weights` startup 검증).
- 사용자 대면 **한국어 라벨 단일 출처: `frontend/types/judge.ts::JUDGE_CRITERIA`** (line 100-107). 백엔드 `judge_adapter.py` 는 영문 키만 그대로 노출 — 라벨링은 순수 프론트 책임 (다른 UI 가 붙으면 라벨 교체 가능한 설계).
- judge 프롬프트(`10/11/12_judge_*.md`)는 영문 키 + 의미 해설만 포함, 한국어 라벨은 없음.

| 영문 키 | 기본 가중치 | UI 한국어 라벨 (frontend/types/judge.ts) | 프롬프트 내 의미 (10_judge_gemini.md 발췌 요약) |
|---|---|---|---|
| `topic_fit` | 20 | **타깃 적합성** | 카테고리·페르소나 적합성. 플러스탭 사용자의 관심사·기대수준 일치 |
| `content_quality` | 25 | **콘텐츠 품질** | 정보 정확성·논리 흐름·실용성. 문장 단위 사실성 + 단계 끊김 없음 |
| `interactivity` | 15 | **인터랙티브** | 인터랙티브 요소가 본문 주제를 행동 전환까지 시키는지 |
| `tone_authenticity` | 20 | **톤 진정성** | 사람이 쓴 글다움 + 플러스탭 캐주얼 톤. LLM 상투구는 감점 |
| `timeliness_trust` | 20 | **출처 신뢰** | 시의성(최근 정보) + 출처 신뢰도(언론사/공공기관·URL 검증) |

### 가중·집계 방식

- 가중치 합 = 100 검증: `validate_judge_weights` (`judge_model_resolver.py:70-89`). 합이 100 ± 0.01 아니면 startup 시 `ValueError`. env override 가능 (`JUDGE_WEIGHTS_TOPIC_FIT` 등).
- 집계 (`judge_panel.py::_compute_aggregate`, 175-242):
  - `mean_scores[dim] = statistics.fmean(vals)` (round 2)
  - `stdev_scores[dim] = statistics.pstdev(vals)` (N=3 가정)
  - `weighted_total = sum(mean[dim] * weight[dim]) / 10` (round 1) — 1–10 점수 × 가중치 합 100 → 결과 스케일 10–100
  - Outlier 판정: `stdev >= 0.5` AND `abs(delta) >= 1.0` → severity medium, `>= 2.0` → high.

### 동시 실행 여부

**Concurrent (`asyncio.gather`)** — `judge_panel.py::JudgePanel.evaluate` (101-161):
```python
tasks = [self._invoke_judge(name, models_used[name], input_html) for name in JUDGE_NAMES]
results = await asyncio.gather(*tasks, return_exceptions=True)
```
각 호출 timeout: `config.timeout_sec` (기본 60초). 하나만 살아도 `status="degraded"`, 전부 실패시 `status="failed"`.

### 예산

`config/agents.yaml::judge_panel.budget_per_run_usd = 0.05` (현재 enforcement 코드 미사용 — 단순 메타).

---

## F4. 운영자 입력 최소화

근거: `backend/config/planning_presets.json`, `backend/api/services/planning_selector.py::PlanningSelector`, `backend/agents/prompts/03_strategy_planner.md`, `frontend/app/page.tsx` + `frontend/components/main/planning-modal.tsx`(미직접확인이지만 page.tsx 참조).

### 운영자가 실제로 선택하는 입력

- **카테고리 1개**: 4 프리셋 (`food`, `ai-trend`, `safety`, `culture`) 또는 `custom`(자유 입력 토픽 텍스트).
  - 근거: `frontend/app/page.tsx::CATEGORY_PRESETS` + `RunManager::CATEGORY_LABEL = {"food":"맛집", "ai-trend":"AI트렌드", "safety":"안전", "culture":"문화", "custom":"자유 입력"}` (run_manager.py:31-37)
  - `custom` 시 `custom_topic` 텍스트가 추가 필수 입력 (generate.py:21-25 validation).
- **선택적 모달 입력 (PlanningModal)**: 프리셋 카테고리 클릭 시 모달이 열려 angle / audience_segment 를 사용자가 수동 지정할 수 있음. 둘 다/한쪽 미지정 = 자동 회전.
  - 근거: `page.tsx::handleConfirmModal` + `run_manager.py::start_run(selection_override=...)` + `planning_selector.py::build_with_override`.
- **그 외 옵션** (max_iter, skip_judge 등): API body 의 `options` 로 per-run override 가능하지만 현재 UI 에서 노출 X (어드민 옵션은 §F7 참조).

### `planning_presets.json` 항목 수

`backend/config/planning_presets.json` 기준:

| 분류 | 항목 수 | 비고 |
|---|---|---|
| `angles` | **9종** (`contrast, ranking, narrative, howto, data, trend, compare, quiz, event_tie`) | 그 중 **`event_tie` 만 `enabled=false`** (disabled). 실제 자동 회전 풀 = 8종. 사용자가 명시 선택해도 `event_tie` 는 `build_with_override` 가 비활성 이유로 ValueError (`planning_selector.py:150-155`). |
| `audience_segments` | **7종** (`twenties_newbie, twenties_student, thirties_single, thirties_worklife, side_hustler, frugal, early_adopter`) | 전부 활성. |
| `rotation` | `{angle: "round_robin", segment: "rotate", dedup_window: 5, campaign_priority: false}` | dedup_window/campaign_priority 는 v2 정책 메타 (현재 사용 X). |

### Strategy Planner angle 주입 + degrade-safe 폴백

- 주입 메커니즘: `concrete_agents.py::_planner_dynamic_vars_factory` 가 4개 placeholder 를 동적으로 채움:
  - `{{INJECTED_ANGLE}}` ← `selection.angle_label`
  - `{{INJECTED_ANGLE_DIRECTIVE}}` ← `selection.angle_directive`
  - `{{INJECTED_SEGMENT}}` ← `selection.segment_label`
  - `{{INJECTED_SEGMENT_PERSONA}}` ← `selection.segment_persona`
- selector 가 None (실패) 이거나 키 누락 시 빈 문자열 주입 → `03_strategy_planner.md` 의 **폴백 분기** 가 발동해 angle/SEG 자율 결정 (회귀 안전). 근거: `_planner_dynamic_vars_factory` 주석 + `run_manager.py:222` `except` 분기.

### 카운터 상태

- 모듈 레벨 인메모리 카운터 (`PlanningSelector._angle_idx`, `_segment_idx`) — 단일 worker 가정 (Procfile `--workers 1`). 재배포 시 0으로 리셋. v2 영속화 예정.

---

## F5. 기술 스택

### 백엔드

근거: `requirements.txt`, `pyproject.toml`, `backend/api/main.py`, `Procfile`, `railway.json`.

| 분류 | 항목 |
|---|---|
| 언어 | Python `>=3.11` (`pyproject.toml:11`, `.python-version` 파일) |
| 웹 프레임워크 | `fastapi>=0.110.0` |
| ASGI 서버 | `uvicorn[standard]>=0.27.0`, `--workers 1 --proxy-headers --forwarded-allow-ips "*"` (Procfile / railway.json) |
| 비동기 모델 | `asyncio` (`asyncio.gather` for Judge Panel, `asyncio.to_thread` for sync pipeline, `asyncio.create_task` for background runs) |
| 스트리밍 | Server-Sent Events (자체 구현 `backend/api/services/sse_broker.py`) |
| LLM SDK | `google-genai>=0.3.0` (Gemini, 신규 SDK — 구 google-generativeai 와 다름), `openai>=1.55.0`, `anthropic>=0.40.0` |
| 데이터 검증 | `pydantic>=2.6.0`, `pydantic-settings>=2.2.0` |
| 설정 | `pyyaml>=6.0.1` (config/*.yaml), `python-dotenv>=1.0.0` (.env) |
| HTTP 클라이언트 | `httpx>=0.27.0` |
| DB | `sqlite3` (표준 라이브러리). 영속: `outputs.db` (종료된 run 의 최종 HTML + 메타만) |
| 데브 도구 | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0`, `ruff>=0.4.0`, `black>=24.3.0` (optional `[dev]`) |
| 코드 스타일 | ruff (line-length=100, py311, select=E,F,I,W,UP,B), black (100) |

### 프론트엔드

근거: `frontend/package.json`.

| 분류 | 항목 |
|---|---|
| 프레임워크 | `next` `14.2.35` (App Router) |
| 런타임 | `react` `^18`, `react-dom` `^18` |
| 데이터 | `@tanstack/react-query` `^5.100.14` |
| UI 컴포넌트 | `shadcn` `^4.8.0`, `@base-ui/react` `^1.5.0`, `class-variance-authority`, `clsx`, `tailwind-merge` |
| 차트 | `recharts` `^3.8.1` |
| 애니메이션 | `framer-motion` `^12.40.0`, `tailwindcss-animate`, `tw-animate-css` |
| 아이콘 | `lucide-react` `^1.16.0` |
| Prompt Editor | `@monaco-editor/react` `^4.7.0` |
| 날짜 | `date-fns` `^4.3.0` |
| Tailwind | `tailwindcss` `^3.4.1` (다크모드: `tailwind.config.ts` 의 `darkMode` 설정 — [확인 필요: 직접 grep 안 함]) |
| TypeScript | `typescript` `^5` |
| Lint | `eslint` `^8`, `eslint-config-next` `14.2.35` |

### 인프라 / 배포

근거: `railway.json`, `Procfile`, `backend/api/main.py`, `backend/storage/outputs_store.py`.

| 항목 | 값/위치 |
|---|---|
| 백엔드 호스팅 | Railway (`railway.json` Nixpacks builder, healthcheck `/api/health` 60s, restart on failure max 3) |
| 프론트엔드 호스팅 | Vercel (`config/deployment.yaml` 의 `production.frontend_url` 빈칸 — 미공개) |
| 백엔드 시작 명령 | `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT --workers 1 --proxy-headers --forwarded-allow-ips "*" --log-level info` |
| 영속 볼륨 | Railway Volume. `OUTPUTS_DB_PATH` 환경변수로 외부 마운트 경로 지정 (`/data/outputs.db` 형태). 미설정 시 `backend/.cache/outputs.db` (컨테이너 재배포 시 휘발) |
| CORS | `API_CORS_ORIGINS` env (기본 `http://localhost:3000,3001,127.0.0.1:3000,3001`) — `backend/api/main.py::_cors_origins` |

### 형상 / Git

- `.gitattributes` 단일 라인: `* text=auto eol=lf` → 저장소 LF 강제.
- `.gitignore` 에 `.env`, `runs/`, `data/`, `.cache/` 등 ignore.
- `pyproject.toml::project.version = "0.1.0"`.

---

## F6. 비용 산정 데이터

근거: `backend/core/cost_tracker.py`, `backend/core/llm_clients.py::estimate_cost` + `_PRICE_TABLE`, `backend/llm/gemini_client.py`, `backend/llm/anthropic_agent_client.py`, `backend/orchestrators/judge_panel.py::_TOKEN_ESTIMATE` + `_JUDGE_PRICE_TABLE`, `backend/api/services/run_manager.py::cost_summary`.

### 1) 토큰 카운트 로직 존재 여부 — **혼합 (실측 가능 인프라는 있으나 실제 9-에이전트 경로에서는 비활성)**

#### 1-A. CostTracker (`backend/core/cost_tracker.py`)

- `record(cost_usd, prompt_tokens, completion_tokens, run_id)` 가 run 단위로 토큰을 누적 (필드: `cost`, `calls`, `prompt_tokens`, `completion_tokens`).
- `snapshot(run_id=...)` 가 `run_prompt_tokens`, `run_completion_tokens`, `run_total_tokens`, `run_cost_usd`, `run_calls` 반환.
- 호출 지점: **`llm_clients.py::call_llm()` 안에서만** `tracker.record(cost, prompt_tokens=p_tok, completion_tokens=c_tok, run_id=run_id)` 호출.
- 즉, **`call_llm()` 을 거치는 호출만 실측됨**.

#### 1-B. 실제 9-에이전트 호출 경로 — **CostTracker 우회 (실측 비활성)**

- `RunManager._run_pipeline` → `build_all_agents(...)` → `concrete_agents.py::make_agent_callable` → 내부에서 `llm_client.call(system_prompt=..., user_input=...)` 호출.
- 이때 `llm_client` 는 `GeminiClient` (`backend/llm/gemini_client.py`) 또는 `AnthropicAgentClient` (`backend/llm/anthropic_agent_client.py`) 인스턴스.
- 두 클래스의 `.call()` 메서드는 SDK 를 **직접 호출**하고 응답을 JSON 파싱 후 반환. **`CostTracker.record` 호출 없음** (grep 검증: `cost_tracker` 의존성은 `core/llm_clients.py`, `core/cost_tracker.py`, `core/base_agent.py`, `core/__init__.py`, `orchestrators/trace_logger.py`, `api/services/run_manager.py` 6 파일에만 존재 — `backend/llm/` 하위 파일에는 없음).
- `core/base_agent.py::Agent.run` 은 `call_llm` 을 거치므로 실측 가능하지만, 현재 production 파이프라인은 `Agent` 클래스가 아니라 `make_agent_callable` (callable factory) 를 사용 — 두 경로가 공존하며 **production 은 후자**.

#### 1-C. 결과적으로 `run_manager.py::cost_summary` 의 값

`run_manager.py:329-371` 의 cost_summary 조립부:

```python
snap = get_cost_tracker().snapshot(run_id=session_id)
newsroom_prompt = int(snap.get("run_prompt_tokens", 0) or 0)
newsroom_completion = int(snap.get("run_completion_tokens", 0) or 0)
...
cost_summary = {
    "newsroom": {..., "is_actual_tokens": True},
    "judge": {..., "is_actual_tokens": False, "note": "... 고정 추정 — 실측 아님"},
    "total": {...},
}
```

- 라벨은 `is_actual_tokens=True` 지만 **실제 record 호출이 없어서 0 으로 수집됨** → 어드민 출력 히스토리 표의 토큰/비용 컬럼이 0/$0.000 으로 표시됨 (UI 0 버그).
- `cost_is_estimated` 플래그 (`outputs.db` 컬럼) 는 `bool(judge_part and judge_part.get("is_actual_tokens") is False)` 로 산정되므로 **판매부에 judge 가 있으면 True**. `cost_summary["newsroom"]` 의 데이터 부족과는 별개로, 단지 "judge 가 추정값을 썼는가" 만 반영.

### 2) 1 run 당 LLM 호출 횟수 (구조적 카운트) — **`[추정 — 실측 불가, 호출 수 기반]`**

각 에이전트는 단계당 1회 호출 가정 (재시도 미포함, 폴백 모델 강등 미포함).

| Stage / Agent | 모델 (별칭 → 실모델) | 호출 횟수 (per run) |
|---|---|---|
| 1-Scout | `gemini_flash` → gemini-2.5-flash | 1 |
| 1-Analyst | `gemini_flash` → gemini-2.5-flash | 1 |
| 1-Planner | `gemini_pro_hi` → gemini-3.1-pro-preview | 1 |
| 2-Writer | `anthropic_sonnet` → claude-sonnet-4-6 | iter × 1 (1~3) |
| 2-Fact-Checker | `gemini_flash` → gemini-2.5-flash | iter × 1 (1~3) |
| 2-Devil's Advocate | `gemini_flash` → gemini-2.5-flash | iter × 1 (1~3) |
| 2-Editor | `anthropic_opus` → claude-opus-4-7 | iter × 1 (1~3) |
| 3-Format Architect | `gemini_pro` → gemini-2.5-pro | 1 |
| 3-HTML Builder | `gemini_pro` → gemini-2.5-pro | 1 |
| 4-Judge Gemini | gemini-2.5-pro (concurrent) | 1 |
| 4-Judge GPT | gpt-5 (concurrent) | 1 |
| 4-Judge Claude | claude-opus-4-7 (concurrent) | 1 |

#### 모델별 호출 분포 표 (best/worst case)

| 모델 | 1-iter (최소) | 2-iter | 3-iter (최대) |
|---|---|---|---|
| `gemini-2.5-flash` (Flash, scout/analyst/factcheck/devils) | 2 + 2×1 = **4** | 2 + 2×2 = **6** | 2 + 2×3 = **8** |
| `gemini-3.1-pro-preview` (Pro Hi, planner) | 1 | 1 | 1 |
| `gemini-2.5-pro` (Pro, architect/builder + judge gemini) | 2 + 1 = **3** | 3 | 3 |
| `claude-sonnet-4-6` (Sonnet, writer) | 1 | 2 | 3 |
| `claude-opus-4-7` (Opus, editor + judge claude) | 1 + 1 = **2** | 2 + 1 = **3** | 3 + 1 = **4** |
| `gpt-5` (judge gpt) | 1 | 1 | 1 |
| **총 호출 횟수** | **12** | **16** | **20** |

- 자동 폴백(503/429) 시 횟수가 추가될 수 있으나 정상 흐름은 위 표.
- `MAX_LLM_CALLS_PER_RUN` 기본값 30 (`backend/core/settings.py::Settings.max_llm_calls_per_run`) — 위 worst case 20 이 한계치 이하.

### 3) Judge Panel 고정 추정값

`backend/orchestrators/judge_panel.py:32`:
```python
_TOKEN_ESTIMATE = {"input": 2000, "output": 1000}
```
모든 judge 호출에 대해 동일 적용. `cost_summary["judge"]["is_actual_tokens"]=False` + `note="judge_panel._TOKEN_ESTIMATE 호출당 input=2000/output=1000 고정 추정 — 실측 아님"` (run_manager.py:362-365).

가격표 (USD per 1M tokens, input/output) — `backend/orchestrators/judge_panel.py::_JUDGE_PRICE_TABLE`:

| model_id | input $/M | output $/M | 호출당 비용 |
|---|---|---|---|
| gemini-2.5-pro | 1.25 | 5.00 | $0.0025 + $0.005 = **$0.0075** |
| gpt-5 | 5.00 | 15.00 | $0.010 + $0.015 = **$0.025** |
| claude-opus-4-7 | 15.00 | 75.00 | $0.030 + $0.075 = **$0.105** |
| **Judge Panel 합계** | — | — | **≈ $0.1375 / run** |

→ `config/agents.yaml::judge_panel.budget_per_run_usd = 0.05` 와 불일치 — 부록 참조.

`backend/core/llm_clients.py::_PRICE_TABLE` 도 별도로 정의 (placeholder 단가):

| model_id | input $/M | output $/M | 비고 |
|---|---|---|---|
| gemini-2.5-pro | 1.25 | 5.00 | — |
| gemini-2.5-flash | 0.075 | 0.30 | — |
| gpt-5 | 5.00 | 15.00 | placeholder 주석 |
| claude-opus-4-7 | 15.00 | 75.00 | placeholder 주석 |
| claude-sonnet-4-6 | 3.00 | 15.00 | placeholder 주석 (Writer 용) |

판매부 dry-run 추정 (`llm_clients.py::_estimate_dry_run_tokens`): in_tokens ≥ max(50, (system+prompt chars)/2), out_tokens = 500 (고정).

### 4) `cost_is_estimated` 의 의미

- DB 컬럼 (`outputs.db::outputs.cost_is_estimated INTEGER`).
- True 가 되는 조건: `run_manager.py:115-117` — `judge_part and judge_part.get("is_actual_tokens") is False`. 즉 **Judge Panel 이 동작한 모든 run**.
- 의미: "judge 토큰은 고정 추정값(2000/1000) 사용 — 실측 아님" (output history UI 의 `est` 배지 title — `frontend/app/admin/runs/page.tsx:182`).
- 9-에이전트(newsroom) 의 실측 누락은 별도 미반영.

---

## F7. 어드민 옵션 (활성 / block 구분)

추출 시점: 2026-06-07. UI 폴리싱 중 — 변동 가능.

근거: `frontend/app/admin/*` + `frontend/components/admin/AdminSidebar.tsx` + `backend/api/routers/{admin_keys,admin_registry,prompts,agents_models,outputs,judges}.py`.

### 사이드바 메뉴 (`AdminSidebar.tsx::NAV`)

| 메뉴 | href | 상태 |
|---|---|---|
| 대시보드 | `/admin` | 활성 (요약 통계 + 빠른 액션 링크) |
| Persona Lab | `/admin/personas` | **활성** |
| 출력 히스토리 | `/admin/runs` | **활성** |
| 발행 이력 | `/admin/registry` | **block (UI 폐쇄)** — "아직 구현중인 메뉴입니다" 안내만 표시. 백엔드 CRUD `/api/admin/registry` 는 살아있음 (admin_registry.py). |
| API 키 | `/admin/keys` | **활성** |
| 운영 옵션 | `/admin/settings` | **부분 활성** — 모든 항목 BLOCKED/decorative (§아래) |

### 페이지별 옵션 / 핸들

#### `/admin/personas` (Persona Lab) — **활성**

- 9 에이전트 + 3 judge = **12개 system prompt 파일 편집** (Monaco Editor).
- 액션: 저장 / 기본값 복원 / 버전 히스토리 보기 / 특정 버전으로 롤백.
- 백엔드: `backend/api/routers/prompts.py` (12 agent_id ↔ 파일 매핑, `.versions/` 백업, `_defaults/` 출고시 스냅샷).
- 영속성: 컨테이너 파일 (재배포 시 초기화 — ephemeral 안내 UI 명시).

#### `/admin/runs` (출력 히스토리) — **활성**

- 영속 저장된 종료 run 리스트 (SQLite `outputs.db` 50건 limit). 컬럼: 토픽 / 카테고리 / 생성 시간 / 종합점수 / 토큰 / 비용 (+`est` 배지) / 미리보기 / 다운로드.
- iframe srcDoc 미리보기 (sandbox="allow-scripts").
- 다운로드: `/api/outputs/{run_id}/download` (Content-Disposition + RFC6266 UTF-8 파일명).

#### `/admin/keys` (API 키) — **활성**

- 3 provider 런타임 키 입력/해제: `gemini`, `openai`, `anthropic`.
- 액션: 적용 (PUT `/api/admin/keys`) / 해제 (DELETE `/api/admin/keys/{provider}` → env 로 복귀).
- 상태 배지: 런타임 설정됨 / env 사용 중 / 미설정.
- 영속성: in-memory only (재시작 시 소실). 평문 응답 금지 — masked 만 노출 (`backend/core/runtime_keys.py::mask`).

#### `/admin/registry` (발행 이력) — **block**

- UI: "🚧 아직 구현중인 메뉴입니다. v2 에서 자동 적재 + 영속화로 제공 예정입니다."
- 백엔드 API (`/api/admin/registry` GET/POST/PATCH/DELETE) + Topic Scout `{{PUBLISHED_TOPICS}}` 동적 주입은 살아있음 (`backend/api/services/topic_registry.py`).

#### `/admin/settings` (운영 옵션) — 전 항목 **BLOCKED 또는 decorative**

상단 경고 배너: "서버 전역 기본값(BLOCKED 표시)을 어드민에서 변경하는 백엔드 엔드포인트는 이번 범위 밖입니다. `.env` / `config/agents.yaml` 을 수정 후 재시작하세요."

**섹션 1 — 파이프라인 (서버 전역 기본값)** — 모두 `blocked`:

| 항목 | 컨트롤 | 기본값 | 상태 |
|---|---|---|---|
| Content Newsroom `max_iter` | select 1/2/3 | 3 | blocked (UI 토글 비활성) |
| `SAFETY_MODE` | select normal/dry_run | normal | blocked |

**섹션 2 — 비용 예산 (USD)** — 모두 `blocked`:

| 항목 | 기본값 | env 키 |
|---|---|---|
| 월간 예산 | 15 | `MONTHLY_BUDGET_USD` |
| 일일 예산 | 2 | `DAILY_BUDGET_USD` |
| Run 당 예산 | 0.5 | `PER_RUN_BUDGET_USD` |

**섹션 3 — 장식 (현재 토글만 동작)** — 모두 `decorative` (UI 상 토글되지만 서버 동작 영향 0):

| 항목 | 컨트롤 |
|---|---|
| 캐시 TTL | select 30s/1m/5m/10m |
| 동시 실행 수 | number 1~8 |
| 로그 레벨 | select DEBUG/INFO/WARNING/ERROR |
| 그라운딩 전역 ON/OFF | toggle |
| Slack Webhook URL | toggle |
| 자동 백업 주기 | select 없음/1h/6h/24h |
| JSON strict 모드 | toggle |
| Streaming 청크 크기 | select 1/5/10/50 |

### 운영 핸들 (메뉴 외)

- **모델 매핑 조회**: `GET /api/agents/models` (frontend 트레이스 뷰어가 에이전트별 model_id 라벨링용으로 사용). UI 편집 X — `config/agents.yaml` 수정 + 재시작 필요.
- **Judge Panel** 모델/가중치 override: env 변수 (`JUDGE_GEMINI_MODEL`, `JUDGE_WEIGHTS_*`). 어드민 UI 노출 X.

---

## F8. 파일/디렉토리 구조 (핵심)

```
aiden/
├── backend/
│   ├── agents/
│   │   ├── concrete_agents.py        # 9 에이전트 callable factory + provider 분기
│   │   ├── definitions.py
│   │   └── prompts/                  # 12 system prompt .md (9 newsroom + 3 judge)
│   │       ├── 01_trend_scout.md … 09_html_builder.md
│   │       ├── 10_judge_gemini.md / 11_judge_gpt.md / 12_judge_claude.md
│   │       ├── _defaults/            # 출고시 스냅샷 (restore 원본)
│   │       └── .versions/            # rollback 백업 (v{N}_{ts}.md)
│   ├── api/
│   │   ├── main.py                   # FastAPI app + CORS + lifespan
│   │   ├── deps.py
│   │   ├── routers/                  # generate, runs, stream(SSE), prompts, judges,
│   │   │                             # personas, agents_models, outputs, planning,
│   │   │                             # admin_keys, admin_registry
│   │   ├── schemas/                  # pydantic 모델
│   │   ├── services/                 # run_manager(백그라운드 실행), sse_broker,
│   │   │                             # trace_converter, humanizer, planning_selector,
│   │   │                             # topic_registry, judge_adapter
│   │   └── utils/                    # trace_loader 등
│   ├── config/
│   │   ├── personas.yaml             # 9 에이전트 페르소나(prefix/suffix 풀)
│   │   ├── planning_presets.json     # 9 angles + 7 segments + rotation
│   │   ├── agent_resources.json      # {{KEY_NAME}} placeholder → 외부 파일 매핑
│   │   └── cdn_urls.json
│   ├── core/
│   │   ├── settings.py               # pydantic-settings + load_*_config()
│   │   ├── llm_clients.py            # call_llm() 통합 wrapper + cost 추정 + dry_run
│   │   ├── cost_tracker.py           # 일일/월간/run 단위 누적 + budget enforcement
│   │   ├── runtime_keys.py           # 런타임 API 키 store (in-memory)
│   │   ├── judge_model_resolver.py   # 3단계 우선순위 (override > env > config)
│   │   ├── anthropic_client.py       # call_anthropic_judge (async, Judge 전용)
│   │   ├── openai_client.py          # call_openai_judge (async, Judge 전용)
│   │   └── base_agent.py             # Agent 베이스 + PromptLoader + WhitelistedSubstitutor
│   ├── llm/
│   │   ├── gemini_client.py          # google-genai 신규 SDK (.call() sync)
│   │   └── anthropic_agent_client.py # Newsroom Writer/Editor 용 (.call() sync)
│   ├── orchestrators/
│   │   ├── base_newsroom.py          # 베이스 (단계 실행 + trace 기록)
│   │   ├── topic_newsroom.py         # Stage 1 (scout → analyst → planner)
│   │   ├── content_newsroom.py       # Stage 2 (3-iter 토론 루프)
│   │   ├── gameifier.py              # Stage 3 (architect → builder, fallback HTML)
│   │   ├── full_pipeline.py          # 1+2+3+선택4 통합
│   │   ├── judge_panel.py            # Stage 4 (asyncio.gather × 3 모델)
│   │   └── trace_logger.py
│   ├── storage/
│   │   └── outputs_store.py          # SQLite 영속 (종료 run 메타 + final_html)
│   ├── templates/                    # plustab_structure.md 등
│   └── tests/                        # pytest (api/, llm/, …)
├── config/                           # 루트 config (브랜드/플랫폼/에이전트 yaml)
│   ├── agents.yaml                   # 모델 별칭 + 에이전트별 매핑 + judge_panel
│   ├── brand.yaml                    # LG U+ 플러스탭 색상/톤
│   ├── platform.yaml                 # A/B/C 콘텐츠 타입 + 인터랙티브 위젯
│   └── deployment.yaml               # local/production URL
├── frontend/
│   ├── app/
│   │   ├── page.tsx                  # 메인 (카테고리 카드 + Recent Runs)
│   │   ├── run/[id]/page.tsx         # SSE 실시간 트레이스 뷰어
│   │   └── admin/
│   │       ├── page.tsx              # 대시보드
│   │       ├── personas/             # Persona Lab (Monaco prompt editor)
│   │       ├── runs/                 # 출력 히스토리 + iframe 미리보기
│   │       ├── keys/                 # API 키 런타임 입력
│   │       ├── registry/             # 발행 이력 (block 안내)
│   │       └── settings/             # 운영 옵션 (전체 BLOCKED/decorative)
│   ├── components/                   # main/, admin/, ui/ (shadcn)
│   ├── lib/                          # api.ts (fetch wrappers), admin-api.ts, constants
│   ├── hooks/
│   └── types/
├── docs/                             # 가이드 + patches 명세서 + samples
├── runs/                             # 트레이스 dump (per session_id 디렉터리)
├── data/                             # gitignore (.gitignore data/)
├── scripts/                          # CLI 진입점들 (run_full_pipeline.py 등)
├── tests/                            # 루트 레벨 pytest
├── CLAUDE.md / PROGRESS.md / README.md
├── .env / .env.example / .gitattributes / .gitignore
├── Procfile / railway.json
├── pyproject.toml / requirements.txt
```

### 핵심 설정 파일 경로

| 용도 | 절대경로(저장소 루트 기준) |
|---|---|
| 9 에이전트 모델 별칭 + 매핑 + Judge Panel | `config/agents.yaml` |
| 9 에이전트 페르소나(말투 풀) + Stage 메타 | `backend/config/personas.yaml` |
| Angle 9종 + SEG 7종 + rotation 정책 | `backend/config/planning_presets.json` |
| Brand 톤/색상 | `config/brand.yaml` |
| Platform 콘텐츠 타입 (A/B/C + 위젯) | `config/platform.yaml` |
| 환경별 URL | `config/deployment.yaml` |
| `{{KEY_NAME}}` placeholder 매핑 | `backend/config/agent_resources.json` |
| 12 system prompt | `backend/agents/prompts/*.md` (+ `.versions/`, `_defaults/`) |
| 영속 출력 SQLite | `backend/.cache/outputs.db` (env `OUTPUTS_DB_PATH` 으로 override — Railway Volume 시 `/data/outputs.db`) |
| 일일 비용 누적 | `backend/.cache/daily_cost.json` (atomic replace) |
| 트레이스 dump (run 별) | `runs/{session_id}/{agents/*.json, metadata.json, judge_panel.json, final_output.html}` |
| FastAPI 진입점 | `backend/api/main.py` (`uvicorn backend.api.main:app`) |
| 환경변수 | `.env` (gitignore. `Settings(BaseSettings)` 가 자동 로드) |

---

## 부록: 추출 중 발견한 불일치/주의점

작성자 노트: "코드 우선" 원칙으로 기록. 운영자가 확인 후 어느 쪽이 옳은지 정정 필요.

### 1. F1 모델 배치 (Writer/Editor Claude 교체 후 잔존 라벨)

- `config/agents.yaml` 의 `gemini_pro_hi` 주석: "B4-S1, 2026-06-05 발화 품질이 핵심인 planner 전용".
- 동일 파일 `anthropic_sonnet`/`anthropic_opus` 주석: "B4-S2, 2026-06-06 Writer/Editor 전용".
- 코드와 yaml 정합 — Writer=`anthropic_sonnet`→claude-sonnet-4-6, Editor=`anthropic_opus`→claude-opus-4-7. 불일치 없음.
- 다만 `backend/config/personas.yaml` 등 일부 문서는 Stage 2 토론을 "iter 1~3" 로 명시. `content_newsroom.py` 의 코드 동작과 일치.

### 2. F2 Devil's Advocate 가중치 5/3/1

- yaml: `devils_advocate_critique_count: {round_1: 5, round_2: 3, round_3: 1}` (단일 출처).
- 코드: `content_newsroom.py::DA_CRITICAL_COUNT_BY_ITER = {1: 5, 2: 3, 3: 1}` + 주석 "참고용 (prompt에 박혀있음)".
- **실 강제는 06_devils_advocate.md system prompt 본문** (코드/yaml 은 메타 보존용). 따라서 yaml 값을 바꿔도 즉시 반영되지 않을 가능성 — 프롬프트 동기화 필요. [확인 필요].

### 3. F3 Judge 5축 한국어 라벨 (2026-06-07 후속 확인 완료)

- 영문 키 5종 + 가중치 단일 출처: `config/agents.yaml::judge_panel.weights`.
- 사용자 대면 **한국어 라벨 단일 출처: `frontend/types/judge.ts::JUDGE_CRITERIA`** (line 100-107) — `topic_fit`="타깃 적합성", `content_quality`="콘텐츠 품질", `interactivity`="인터랙티브", `tone_authenticity`="톤 진정성", `timeliness_trust`="출처 신뢰".
- 백엔드 `judge_adapter.py` 는 영문 키만 그대로 노출 — 한국어 라벨 매핑 없음 (UI 책임).
- 초안 추출 시 추정 라벨("주제 적합도/톤·진정성/시의성·신뢰")이 일부 실제와 다름 (구체 차이는 본 보고의 추가 정정 표 참조). **본 문서 F3 본문은 정정 반영 완료**.

### 4. F4 `event_tie` 의 disabled 상태와 사용자 명시 선택

- `planning_presets.json::angles[8]` 의 `event_tie` 만 `enabled=false`. 자동 회전 풀에서 제외 (`_enabled_angles`).
- 그러나 `planning_selector.py::build_with_override:150-155` 에서 사용자가 명시적으로 `event_tie` 를 선택해도 `ValueError("angle key 비활성 — 사용 불가")` 로 차단됨 — 즉 "disabled 항목은 자동/수동 모두 차단" 정책. UI 측에서 disabled 항목을 회색/숨김 처리하는지는 `frontend/components/main/planning-modal.tsx` 직접 확인 필요. [확인 필요].

### 5. F5 다크모드 / 폰트

- `tailwind.config.ts` 의 darkMode 설정 직접 확인하지 않음 — package.json 의 의존성에 `tw-animate-css`, `tailwindcss-animate` 만 보임. globals.css 의 CSS 변수가 다크 팔레트 — 본 추출 미상세. [확인 필요].

### 6. F6 — **최대 불일치: newsroom 토큰 실측 불가**

- 명세상 의도: `CostTracker` 가 모든 LLM 호출의 prompt/completion 토큰을 run 단위로 누적해야 함 (필드는 존재 — `prompt_tokens`, `completion_tokens`).
- 실제: production 9-에이전트 경로(`make_agent_callable` → `GeminiClient.call` / `AnthropicAgentClient.call`)는 **`call_llm` 을 우회**하여 SDK 직접 호출 → `CostTracker.record` 미호출 → `snap.run_prompt_tokens` 가 0 반환.
- 따라서 `run_manager.py::cost_summary["newsroom"]["is_actual_tokens"]=True` 라벨은 **명목상**이며, 실 가치는 0/0/0/$0.000.
- `cost_is_estimated` 컬럼은 judge 만 추적하므로 newsroom 의 실측 부재는 별도 미반영 — 출력 히스토리 UI 가 작은 토큰/비용 + `est` 배지를 보여줄 수 있음.
- 해결책 (정보): (a) `make_agent_callable` 가 GeminiClient/AnthropicAgentClient 결과의 usage 메타를 추출해 직접 `CostTracker.record(run_id=...)` 호출, 또는 (b) production 을 `Agent` 클래스(`base_agent.py`) 기반으로 전환. 단, **본 작업 범위는 추출 전용이므로 코드 수정 안 함**.

### 7. F6 — Judge 예산 표기 불일치

- yaml: `judge_panel.budget_per_run_usd = 0.05`.
- 코드 추정: 3 judge × (2000 in / 1000 out) × 단가 = **≈ $0.1375 / run** (Opus 4.7 의 단가가 압도적).
- 예산보다 추정 비용이 약 2.75× 큼. 현재 budget enforcement 코드 미사용이라 실제 차단은 안 됨 — 단순 메타로 둔 상태로 보임. [확인 필요: budget 의도가 무엇이었는지].

### 8. F6 — `cost_is_estimated` 의 범위 불일치

- 의도된 의미(현행): "judge 토큰이 추정값인가?" → newsroom 실측 여부와 무관.
- 운영 관점에서 보기 헷갈림 — newsroom 자체가 실측이 아닌데 (위 6번) 컬럼 이름이 일반적이라 오해 소지. UI 의 `est` 배지 title 에는 정확히 "judge 토큰은 호출당 고정 추정값 사용" 으로 명시됨 — UX 측은 OK.

### 9. F7 — Persona Lab 의 "기본값 복원" 동작

- `_defaults/` 폴더는 **최초 부팅 시 1회** 생성 (`prompts.py::_ensure_defaults_snapshot`). 이미 존재하면 skip — 진정한 "출고시 디폴트" 보장.
- 그러나 `_defaults/` 가 만들어진 시점이 (a) v0 정식 출고일이 아니라 (b) **현재 서버를 가장 먼저 띄운 시점의 prompts/ 상태** 임을 의미 → 재배포 시 컨테이너 새 파일시스템이라 _defaults 도 새로 만들어짐. 영속 볼륨 없으면 "기본값" 의 의미가 컨테이너 수명에 종속.
- ephemeral 안내 배너는 이 사실을 사용자에게 명시.

### 10. F7 — `/admin/registry` UI 폐쇄 vs 백엔드 살아있음

- UI 는 "🚧 아직 구현중" 안내만 표시.
- 백엔드 라우터 (`backend/api/routers/admin_registry.py`) 는 GET/POST/PATCH/DELETE 전부 라이브.
- 게다가 Topic Scout 의 `{{PUBLISHED_TOPICS}}` 동적 주입 (`concrete_agents.py::_scout_dynamic_vars`) 도 동작하여, 누군가 `curl` 등으로 직접 POST 하면 발행 토픽 회피 기능은 작동함.
- 데모 동선상 노출 안 하기로 한 의도적 dead UI.

---

## `[확인 불가]` / `[확인 필요]` 항목 모음

| 항목 | 사유 | 권장 액션 |
|---|---|---|
| ~~F3 Judge 5축 한국어 정확 라벨~~ | **해결됨 (2026-06-07)** — `frontend/types/judge.ts::JUDGE_CRITERIA` 가 SSOT. 본문 정정 반영 완료. | — |
| F2 Devil's Advocate critique 개수 강제 지점 | 코드 주석은 "prompt 에 박혀있음" 이라 함 — 실제 prompt 본문 미확인 | `backend/agents/prompts/06_devils_advocate.md` 의 라운드별 개수 명시 grep |
| F4 UI 의 `event_tie` disabled 처리 | `frontend/components/main/planning-modal.tsx` 미read | 해당 컴포넌트 직접 확인 |
| F5 Tailwind 다크모드 활성 여부 | `tailwind.config.ts` 미 read | 직접 확인 |
| F6 newsroom 실측 누락 수정 의도 | 명세 부재 — 의도된 미구현인지 버그인지 불명 | 운영자/스펙 작성자에 확인 |
| F6 Judge `budget_per_run_usd=0.05` 의도 | 추정 비용 $0.1375 와 불일치 — enforcement 코드 미사용 | 운영자 확인 |

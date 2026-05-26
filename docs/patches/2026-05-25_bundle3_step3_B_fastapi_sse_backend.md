# 묶음 3 Step 3-B: FastAPI SSE 엔드포인트 + Trace 직렬화

- **ID**: B3-S3-B
- **우선순위**: 묶음 3 우선순위 4 의 두번째 분할 명세
- **의존**: B3-S3-A (Next.js 프론트엔드 셋업) 완료, B3-S2 (Judge Panel) 완료
- **목적**:
  1. 프론트엔드 ↔ 백엔드 연결 (FastAPI 서버 + REST + SSE)
  2. FullPipeline 실시간 trace 를 SSE 로 스트리밍
  3. Judge Panel 결과 + 최근 실행 목록 + system prompt CRUD API 제공
  4. 다음 명세 (B3-S3-C 트레이스 뷰어) 가 의존할 데이터 흐름 확정
- **상위 마스터**: `docs/patches/2026-05-25_bundle3_step3_admin_ui_master_v2.md`

---

## 작업 범위

| 영역 | 포함 | 제외 (다른 명세) |
|---|---|---|
| FastAPI 서버 | uvicorn 실행, CORS, 에러 핸들링 | 인증·인가 (마감 후) |
| REST 엔드포인트 | generate, runs, prompts CRUD, judge | — |
| SSE 엔드포인트 | trace 실시간 스트리밍 | 실시간 비용 모니터링 (B3-S3-E) |
| Trace 직렬화 | 채팅 버블용 사람말투 변환 | UI 렌더링 (B3-S3-C) |
| 프론트 연결 | API 클라이언트 + React Query 셋업 | 트레이스 뷰어 UI (B3-S3-C) |
| 백그라운드 작업 | asyncio 기반 FullPipeline 실행 | Celery·Redis (overkill, 마감 후) |

---

## 폴더 구조 (백엔드)

```
backend/
├── api/                            # 신규
│   ├── __init__.py
│   ├── main.py                     # FastAPI 앱 진입점
│   ├── deps.py                     # 공통 의존성 (settings, run manager)
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── generate.py             # POST /api/generate
│   │   ├── runs.py                 # GET /api/runs, /api/runs/{id}
│   │   ├── stream.py               # GET /api/stream/{session_id} (SSE)
│   │   ├── prompts.py              # GET/PUT /api/prompts/{agent_id}
│   │   └── judges.py               # GET /api/runs/{id}/judge
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── generate.py             # GenerateRequest/Response
│   │   ├── run.py                  # RunSummary, RunDetail
│   │   ├── trace.py                # ChatMessage (SSE payload)
│   │   ├── judge.py                # JudgePanel 직렬화
│   │   └── prompt.py               # PromptDetail, PromptUpdate
│   ├── services/
│   │   ├── __init__.py
│   │   ├── run_manager.py          # 백그라운드 실행 관리 (asyncio.Task 추적)
│   │   ├── trace_converter.py      # raw trace JSON → ChatMessage
│   │   └── sse_broker.py           # SSE pub/sub (asyncio.Queue 기반)
│   └── utils/
│       ├── __init__.py
│       └── trace_loader.py         # runs/<session>/ 파일 읽기
└── tests/api/                      # 신규
    ├── __init__.py
    ├── test_generate.py
    ├── test_runs.py
    ├── test_stream.py
    ├── test_prompts.py
    └── test_trace_converter.py
```

추가로 루트에 `scripts/run_api_server.py` 신규 (uvicorn 실행 헬퍼).

---

## 엔드포인트 명세

### 1. `POST /api/generate` — 콘텐츠 생성 시작

**Request:**
```json
{
  "category": "food | ai-trend | safety | culture | custom",
  "custom_topic": "string (category=custom 일 때만)",
  "options": {
    "max_iter": 3,
    "skip_judge": false,
    "safety_mode": "normal | dry_run"
  }
}
```

**Response (즉시 반환, 백그라운드 실행 시작):**
```json
{
  "session_id": "2026-05-26T15-32-10_abc12345",
  "status": "started",
  "stream_url": "/api/stream/2026-05-26T15-32-10_abc12345",
  "started_at": "2026-05-26T15:32:10Z"
}
```

**동작:**
- session_id 생성 → `run_manager.start_run()` 호출 → asyncio.Task 로 FullPipeline 비동기 실행
- 즉시 응답 반환 (실행 완료 대기 안 함)
- 실패 시 (예: API 키 누락) HTTP 500 + 에러 메시지

---

### 2. `GET /api/stream/{session_id}` — SSE 트레이스 스트리밍

**Response: Server-Sent Events 스트림**

이벤트 유형:

#### `chat` — 채팅 버블용 메시지
```
event: chat
data: {
  "id": "msg-001",
  "agent_id": "scout",
  "stage": 1,
  "iteration": null,
  "timestamp": "2026-05-26T15:32:15Z",
  "duration_ms": 3245,
  "headline": "트렌드 3개 확보. 1위: '편의점 신상 디저트'",
  "body_text": "검색 결과 분석 완료. 후보 3개 중 빕 구르망 트렌드가 가장 강함.",
  "raw_json": { ... 원본 agent output ... },
  "highlights": [
    {"label": "검색 호출", "value": "5회"},
    {"label": "신뢰도", "value": "0.92"}
  ],
  "badges": [
    {"label": "confidence", "value": "high", "color": "success"}
  ]
}
```

#### `stage_change` — Stage 진행 변경
```
event: stage_change
data: {
  "stage": 2,
  "stage_name": "Content Newsroom",
  "previous_stage": 1,
  "timestamp": "..."
}
```

#### `iteration_start` — Stage 2 iter 시작
```
event: iteration_start
data: {
  "stage": 2,
  "iteration": 2,
  "timestamp": "..."
}
```

#### `cost_update` — 누적 비용 갱신
```
event: cost_update
data: {
  "total_usd": 0.0123,
  "budget_usd": 0.50,
  "elapsed_ms": 142000,
  "last_latency_ms": 3245
}
```

#### `judge_evaluation` — Judge Panel 평가 도착 (Stage 4)
```
event: judge_evaluation
data: {
  "model": "gemini | gpt | claude",
  "overall_score": 7.6,
  "scores": { ... },
  "one_line_verdict": "...",
  "completed_count": 1,
  "total_count": 3
}
```

#### `pipeline_complete` — 실행 종료
```
event: pipeline_complete
data: {
  "status": "completed | partial | failed",
  "final_output_url": "/api/runs/<id>/output",
  "judge_summary": {
    "weighted_total": 73.4,
    "status": "completed"
  },
  "duration_ms": 372000,
  "total_cost_usd": 0.0254
}
```

#### `error` — 오류
```
event: error
data: {
  "agent_id": "fact_checker",
  "stage": 2,
  "iteration": 3,
  "error_message": "Gemini API 503",
  "retry_count": 1,
  "is_recoverable": true
}
```

---

### 3. `GET /api/runs` — 최근 실행 목록

**Query params:** `limit=10`, `category=food`, `status=completed` (모두 optional)

**Response:**
```json
{
  "runs": [
    {
      "session_id": "...",
      "category": "food",
      "title": "가족 식비, 매달 50만원 아끼는 법",
      "status": "completed",
      "started_at": "...",
      "duration_ms": 372000,
      "judge_weighted_total": 73.4,
      "judge_status": "completed",
      "thumbnail_url": null
    }
  ],
  "total": 7
}
```

**구현:** `runs/` 폴더 스캔 + 각 session 의 `metadata.json` 파싱

---

### 4. `GET /api/runs/{session_id}` — 단일 실행 상세

**Response:** 전체 trace + judge_panel 통합. 페이지 새로고침 또는 직접 링크 접속 시 SSE 끊김 복구용.

```json
{
  "session_id": "...",
  "category": "...",
  "status": "completed",
  "started_at": "...",
  "duration_ms": 372000,
  "messages": [ ... 변환된 ChatMessage 배열 (전체 trace) ... ],
  "stages": [
    {"stage": 1, "status": "completed", "duration_ms": 32000, "agents_completed": 3},
    {"stage": 2, "status": "completed", "duration_ms": 180000, "iterations": 3},
    ...
  ],
  "judge_panel": { ... B3-S2 judge_panel.json 그대로 ... },
  "final_output_html_url": "/api/runs/<id>/output",
  "metadata": { ... metadata.json 전체 ... }
}
```

---

### 5. `GET /api/runs/{session_id}/output` — 최종 HTML 반환

**Response:** `final_output.html` 파일 그대로 (Content-Type: text/html)

iframe 미리보기용.

---

### 6. `GET /api/runs/{session_id}/judge` — Judge Panel 결과만 분리

**Response:** `judge_panel.json` 그대로 (편의 API, 어드민 UI 카드용)

---

### 7. `GET /api/prompts` — 12 에이전트 prompt 목록

**Response:**
```json
{
  "prompts": [
    {
      "agent_id": "scout",
      "filename": "01_trend_scout.md",
      "path": "backend/agents/prompts/01_trend_scout.md",
      "size_bytes": 3421,
      "last_modified": "2026-05-23T10:12:00Z",
      "version_count": 5
    },
    ...
  ]
}
```

---

### 8. `GET /api/prompts/{agent_id}` — 단일 prompt 내용

**Response:**
```json
{
  "agent_id": "scout",
  "content": "# Trend Scout 🔍\n\n당신은...",
  "size_bytes": 3421,
  "last_modified": "2026-05-23T10:12:00Z",
  "detected_variables": ["TONE_REFERENCE"],
  "estimated_tokens": 2341
}
```

---

### 9. `PUT /api/prompts/{agent_id}` — prompt 수정 (Hot Reload)

**Request:**
```json
{
  "content": "# Trend Scout (modified)...",
  "save_version": true
}
```

**Response:**
```json
{
  "agent_id": "scout",
  "saved_at": "...",
  "size_bytes": 3500,
  "version_id": "v6",
  "diff_summary": "+5 lines, -2 lines"
}
```

**동작:**
- 파일 백업 (`backend/agents/prompts/.versions/01_trend_scout_v5_<timestamp>.md`)
- 새 내용 저장
- PromptLoader 캐시 무효화 (다음 실행부터 반영)

---

### 10. `GET /api/health` — 헬스 체크

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_sec": 1234,
  "active_runs": 1,
  "judge_panel_available": true
}
```

---

## Trace 변환 룰 (raw JSON → ChatMessage)

`backend/api/services/trace_converter.py` 에 핵심 로직.

### 변환 패턴 예시

#### Trend Scout
**Raw:**
```json
{
  "trending_topics": [
    {"title": "편의점 신상 디저트", "confidence": 0.92, "sources": [...]},
    ...
  ],
  "search_queries_used": ["편의점 디저트 신상", ...]
}
```

**Converted:**
```python
ChatMessage(
    agent_id="scout",
    headline=f"트렌드 {len(topics)}개 확보. 1위: '{topics[0]['title']}'",
    body_text=f"검색 결과 분석 완료. 후보 {len(topics)}개 중 '{top['title']}' 가 가장 강함.",
    highlights=[
        {"label": "검색 호출", "value": f"{len(queries)}회"},
        {"label": "1위 신뢰도", "value": f"{top['confidence']:.2f}"},
    ],
    badges=[
        {"label": "confidence", "value": "high" if top['confidence'] > 0.8 else "medium"},
    ],
    raw_json=raw,
)
```

#### Fact-Checker
**Raw:**
```json
{
  "confidence_score": 8,
  "verification_log": [
    {"claim": "...", "status": "verified", ...},
    {"claim": "...", "status": "verified", ...},
  ],
  "annotated_draft": { ... },
  "summary": "..."
}
```

**Converted:**
```python
verified_count = sum(1 for v in log if v["status"] == "verified")
total_count = len(log)
ChatMessage(
    agent_id="factchecker",
    headline=f"{verified_count}/{total_count} 검증 완료. 신뢰도 {confidence}/10",
    body_text=raw["summary"],
    highlights=[
        {"label": "검증 완료", "value": f"{verified_count}/{total_count}"},
        {"label": "confidence", "value": f"{confidence}/10"},
    ],
    badges=[
        {"label": "score", "value": f"{confidence}/10", "color": "success" if confidence >= 7 else "warning"},
    ],
)
```

#### Devil's Advocate
**Raw:**
```json
{
  "critical_issues": [...5건...],
  "average_score": 6.2,
  "pass_threshold": 6,
  "pass": true
}
```

**Converted:**
```python
top_critique = raw["critical_issues"][0]["issue"] if raw["critical_issues"] else ""
ChatMessage(
    agent_id="devils",
    headline=f"{len(critical_issues)}건 까겠습니다. 평균 {avg_score}",
    body_text=f"1번: {top_critique[:80]}...",
    badges=[
        {"label": "pass", "value": "통과" if pass_ else "재작성", "color": "success" if pass_ else "danger"},
        {"label": "avg", "value": f"{avg_score:.1f}"},
    ],
)
```

#### Editor-in-Chief
**Raw:**
```json
{
  "decision": "needs_revision | approved",
  "accepted_critiques": [...],
  "rejected_critiques": [...],
  "revision_instructions": [...],
  "final_content": { ... }
}
```

**Converted:**
```python
decision_label = {"approved": "승인", "needs_revision": "재작성"}[raw["decision"]]
ChatMessage(
    agent_id="editor",
    headline=f"iter {iteration} 결정: {decision_label}",
    body_text=f"비판 {len(accepted)}건 수용, {len(rejected)}건 기각.",
    highlights=[...],
    badges=[
        {"label": "decision", "value": decision_label, "color": "success" if approved else "warning"},
    ],
)
```

#### Judge 3 모델 공통
**Raw:** B3-S2 의 evaluations.{model} 그대로

**Converted:**
```python
ChatMessage(
    agent_id=f"judge-{model}",
    headline=f"⭐ {overall_score} / 10 · {one_line_verdict}",
    body_text=f"강점: {len(strengths)}건 / 약점: {len(weaknesses)}건",
    highlights=[
        {"label": "topic_fit", "value": scores["topic_fit"]},
        ...
    ],
    badges=[
        {"label": "verdict", "value": f"{overall_score}/10"},
    ],
)
```

전체 변환 매핑은 12 에이전트 × 변환 함수로 1:1 매핑. `trace_converter.py` 에 dispatch 테이블.

---

## SSE Broker 설계 (`sse_broker.py`)

```python
import asyncio
from typing import AsyncIterator

class SSEBroker:
    """asyncio.Queue 기반 pub/sub.
    
    FullPipeline 이 trace_logger 를 통해 메시지 push,
    SSE 엔드포인트가 subscribe 해서 클라이언트에 전달.
    """
    
    def __init__(self):
        self._channels: dict[str, list[asyncio.Queue]] = {}
    
    async def publish(self, session_id: str, event_type: str, data: dict):
        for queue in self._channels.get(session_id, []):
            await queue.put({"event": event_type, "data": data})
    
    async def subscribe(self, session_id: str) -> AsyncIterator[dict]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._channels.setdefault(session_id, []).append(queue)
        try:
            while True:
                msg = await queue.get()
                if msg.get("event") == "_close":
                    return
                yield msg
        finally:
            self._channels[session_id].remove(queue)
            if not self._channels[session_id]:
                del self._channels[session_id]
    
    async def close(self, session_id: str):
        await self.publish(session_id, "_close", {})
```

---

## TraceLogger 후킹

`backend/orchestrators/trace_logger.py` 수정 (기존 동작 유지 + SSE broker 호출 추가):

```python
class TraceLogger:
    def __init__(self, session_id: str, sse_broker: SSEBroker | None = None):
        # ... 기존 코드 ...
        self._sse_broker = sse_broker  # 선택적 주입
    
    async def log_agent_call(self, ...):
        # 1. 기존: 파일 저장 (JSON + summary.jsonl)
        self._save_to_file(...)
        
        # 2. 신규: SSE broker 가 있으면 publish
        if self._sse_broker:
            chat_message = trace_converter.convert(agent_output, agent_id, ...)
            await self._sse_broker.publish(
                self.session_id,
                "chat",
                chat_message.dict(),
            )
```

**중요**: TraceLogger 가 sync 였다면 async 로 마이그레이션 필요. 기존 회귀 테스트 영향 확인.

---

## Run Manager (`run_manager.py`)

```python
class RunManager:
    def __init__(self, sse_broker: SSEBroker):
        self._active_runs: dict[str, asyncio.Task] = {}
        self._sse_broker = sse_broker
    
    async def start_run(self, session_id: str, category: str, options: dict) -> None:
        async def _run():
            try:
                pipeline = FullPipeline(
                    session_id=session_id,
                    sse_broker=self._sse_broker,  # 신규
                )
                result = await pipeline.run(category=category, **options)
                await self._sse_broker.publish(
                    session_id, "pipeline_complete",
                    {"status": result.status, ...}
                )
            except Exception as e:
                await self._sse_broker.publish(
                    session_id, "error", {"error_message": str(e)}
                )
            finally:
                await self._sse_broker.close(session_id)
                self._active_runs.pop(session_id, None)
        
        task = asyncio.create_task(_run())
        self._active_runs[session_id] = task
    
    def get_active_runs(self) -> list[str]:
        return list(self._active_runs.keys())
```

---

## 프론트엔드 API 클라이언트 (`frontend/lib/api.ts` 신규)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function startGenerate(req: GenerateRequest): Promise<GenerateResponse> {
  const res = await fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchRecentRuns(limit = 10): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE}/api/runs?limit=${limit}`);
  return res.json();
}

export async function fetchRunDetail(sessionId: string): Promise<RunDetail> {
  const res = await fetch(`${API_BASE}/api/runs/${sessionId}`);
  return res.json();
}

export function subscribeRunStream(
  sessionId: string,
  handlers: {
    onChat?: (msg: ChatMessage) => void;
    onStageChange?: (data: StageChangeData) => void;
    onJudge?: (data: JudgeEvalData) => void;
    onComplete?: (data: CompleteData) => void;
    onError?: (data: ErrorData) => void;
  }
): () => void {
  const url = `${API_BASE}/api/stream/${sessionId}`;
  const es = new EventSource(url);
  
  es.addEventListener("chat", (e) => handlers.onChat?.(JSON.parse(e.data)));
  es.addEventListener("stage_change", (e) => handlers.onStageChange?.(JSON.parse(e.data)));
  es.addEventListener("judge_evaluation", (e) => handlers.onJudge?.(JSON.parse(e.data)));
  es.addEventListener("pipeline_complete", (e) => {
    handlers.onComplete?.(JSON.parse(e.data));
    es.close();
  });
  es.addEventListener("error", (e) => {
    if (es.readyState === EventSource.CLOSED) return;
    handlers.onError?.(JSON.parse((e as MessageEvent).data || "{}"));
  });
  
  return () => es.close();
}
```

---

## 메인 페이지 연동 (B3-S3-A 결과물 수정)

`frontend/app/page.tsx` 의 다음 부분 mock → 실제 API 로 교체:

| 위치 | 기존 (B3-S3-A) | 신규 (B3-S3-B) |
|---|---|---|
| 최근 실행 5건 | `MOCK_RECENT_RUNS` | `fetchRecentRuns(5)` (React Query) |
| Generate 버튼 클릭 | `router.push(\`/run/\${mockId}\`)` | `startGenerate()` → 응답의 session_id 로 `router.push` |

mock 데이터는 fallback 으로 유지 (API 미응답 시 표시).

---

## 환경 변수

`backend/.env` 추가 (.env.example 갱신):
```
# API 서버
API_HOST=0.0.0.0
API_PORT=8000
API_CORS_ORIGINS=http://localhost:3000,http://localhost:3001
API_LOG_LEVEL=info
```

`frontend/.env.local.example` 추가:
```
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

---

## 단위 테스트

### test_trace_converter.py (9건 — 12 에이전트 중 핵심 9개 변환)
| # | 케이스 |
|---|---|
| 1 | Trend Scout 변환 |
| 2 | Audience Analyst 변환 |
| 3 | Strategy Planner 변환 |
| 4 | Writer 변환 (iter 1) |
| 5 | Fact-Checker 변환 (verified 카운트) |
| 6 | Devil's Advocate 변환 (pass=true/false 분기) |
| 7 | Editor-in-Chief 변환 (approved / needs_revision 분기) |
| 8 | HTML Builder 변환 |
| 9 | Judge (Gemini/GPT/Claude) 변환 |

### test_runs.py (4건)
| # | 케이스 |
|---|---|
| 1 | runs/ 폴더 스캔 → 메타데이터 추출 |
| 2 | category 필터 동작 |
| 3 | judge_weighted_total 정확 추출 |
| 4 | 빈 runs/ 폴더 (200 + empty list) |

### test_stream.py (3건)
| # | 케이스 |
|---|---|
| 1 | SSE 연결 후 chat 이벤트 수신 |
| 2 | pipeline_complete 후 자동 close |
| 3 | 존재하지 않는 session_id → 404 |

### test_prompts.py (3건)
| # | 케이스 |
|---|---|
| 1 | 12 에이전트 목록 응답 |
| 2 | 단일 prompt 내용 + detected_variables 추출 |
| 3 | PUT 으로 수정 → 백업 파일 생성 확인 |

### test_generate.py (2건)
| # | 케이스 |
|---|---|
| 1 | POST → 즉시 session_id 응답 + 백그라운드 시작 |
| 2 | 잘못된 category → 422 |

---

## 검증 방법

### Step 1. 구현
- 신규 파일 약 25개 (백엔드 + 프론트 + 테스트)
- 단위 테스트 21건 통과
- 회귀 테스트 (기존 49건) 통과 — TraceLogger 비동기화 영향 확인

### Step 2. API 서버 실행
```bash
python scripts/run_api_server.py
# 또는 uvicorn backend.api.main:app --reload --port 8000
```
→ `http://localhost:8000/api/health` 200 응답

### Step 3. OpenAPI docs 검증
- `http://localhost:8000/docs` 접속
- 10개 엔드포인트 모두 표시
- Try it out 으로 GET /api/runs 호출 → mock 데이터 OK 시 1건 이상 반환

### Step 4. 프론트엔드 연동
```bash
cd frontend
npm run dev
```
- 메인 페이지 → 최근 실행 5건이 mock 이 아닌 **실제 API 응답** 으로 표시
- "Generate" 클릭 → `/run/<실제_session_id>` 로 라우팅 (트레이스 뷰어 UI 는 B3-S3-C 에서 구현, placeholder 표시)

### Step 5. SSE 통합 테스트
- POST /api/generate 호출 → session_id 받음
- curl 또는 브라우저로 `GET /api/stream/<session_id>` 접속
- 9 에이전트 trace 이벤트 순차 도착 확인 (chat, stage_change, cost_update, judge_evaluation, pipeline_complete)
- 종료 후 SSE 자동 close

### Step 6. CORS
- 프론트 (localhost:3000 또는 3001) 에서 백엔드 (localhost:8000) 호출 시 CORS 에러 없음 확인

---

## 위험 / 제약

### 1. TraceLogger 비동기화
기존 동기 함수 → async 마이그레이션 시 회귀 테스트 영향. 마이그레이션 전후 비교 필수.

**대안**: TraceLogger 자체는 동기 유지하고, SSE publish 만 `asyncio.create_task` 로 fire-and-forget. 단 이벤트 순서 보장 안 됨 (큐 기반이라 큰 영향 없음).

**추천: 대안 채택** (작업량 ↓, 안정성 ↑).

### 2. FullPipeline 의 asyncio 호환
기존 FullPipeline 이 sync 라면 백그라운드 실행 시 `asyncio.to_thread` 래핑 필요. 또는 FullPipeline 도 async 화.

**확인 필요**: 현재 FullPipeline 의 동기·비동기 상태 (Claude Code 가 작업 전 점검).

### 3. 백그라운드 작업 안정성
asyncio.Task 가 무한 대기·예외 누수 가능성. 모든 task 에 timeout (max 20분) + 예외 catch 필수.

### 4. CORS 정책
개발 환경에선 `localhost:3000,3001` 허용. 프로덕션 배포 시 제한 필요 (마감 후).

### 5. SSE 연결 유지
브라우저 idle timeout 대비 30초마다 ping 이벤트 발송 (heartbeat).

---

## Claude Code 실행 지시

1. 시작 전 점검:
   - `backend/orchestrators/full_pipeline.py` 의 sync/async 상태 확인
   - `backend/orchestrators/trace_logger.py` 의 인터페이스 확인
   - 결과를 보고서 시작 부분에 명시

2. TraceLogger 수정 방식 결정:
   - **추천: 대안 채택** (sync 유지 + asyncio.create_task fire-and-forget)
   - 채택 안 한다면 이유 보고

3. 백엔드 신규 파일 약 18개 + 수정 파일 약 3개 작업

4. 프론트엔드 수정:
   - `frontend/lib/api.ts` 신규
   - `frontend/app/page.tsx` API 연동
   - React Query 추가 (`@tanstack/react-query`)
   - `.env.local.example` 추가

5. 단위 테스트 21건 작성 + 통과 확인 (백엔드만, 프론트 테스트는 생략)

6. 회귀 테스트 통과 확인 (기존 49건)

7. API 서버 + 프론트 동시 실행해서 통합 검증:
   - `/api/health` 응답
   - `/docs` OpenAPI UI
   - 메인 페이지 → API 호출 → 최근 실행 표시
   - 실제 LLM 호출 없이도 mock runs 폴더 데이터로 검증 가능

8. 보고:
   - 신규/수정 파일 절대 경로 + 라인 수
   - 단위 테스트 21건 결과
   - 회귀 테스트 결과
   - API 서버 실행 로그 + 헬스 체크 응답
   - 프론트 ↔ 백 통합 검증 결과 (curl 명령 또는 시각 검증)
   - **실제 LLM 호출은 하지 말 것** (POST /api/generate 시 dry_run 모드 또는 mock 응답)

9. **git add / commit / stage 금지**

---

## 후속 작업

- **B3-S3-C**: 트레이스 뷰어 (`/run/<session_id>` UI 구현, SSE 연결, 채팅 버블 시각화)
- **B3-S3-D**: Judge 시각화 (시뮬레이션 + 레이더 차트)
- **B3-S3-E**: Persona Lab + 운영 페이지들

---

## 별도 이슈

- **#api-auth**: 인증·인가. 마감 직전 단순 password gate
- **#sse-heartbeat**: 30초 ping 이벤트. 마감 임박 시 검토
- **#fullpipeline-async**: FullPipeline async 화 검토 (현재는 to_thread 래핑으로 우회)

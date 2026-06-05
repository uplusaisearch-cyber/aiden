# B3-S3-E — 어드민 운영 콘솔 (Persona Lab + API키 + 발행 이력)

> **작성**: 2026-06-04 · **갱신**: 2026-06-05 (배포 환경 회귀 점검 2건 추가) · **대상**: AIDEN admin UI 최종 묶음 (E)
> **실행 모드**: 사용자 부재 자율 진행. BLOCKED/REGRESSION 외에는 끝까지 멈추지 말 것.
> **마감**: 6/8. 이 묶음 완료가 어드민 UI의 마지막 구현 단위.

---

## ⚠️ 갱신 사항 (2026-06-05) — 배포 환경 전제

이 시스템은 현재 **Railway(백엔드) + Vercel(프론트)에 배포 완료된 상태**다. 로컬 데모가 1순위이나 배포 URL도 살아있다. 따라서 아래 2가지를 작업 전 인지하고, §7 회귀 점검에 추가된 항목을 반드시 지킬 것.

1. **[회귀 위험] A2 API 키 조회 경로 변경이 healthcheck 를 깨면 배포 전체가 마비된다.**
   - `/api/health` 가 `JudgePanel.from_settings()` 로 키를 읽어 `judge_panel_available` 을 판정하고, Railway 가 `/api/health` 를 healthcheck 로 쓴다.
   - A2 가 LLM 키 조회를 "런타임 override > env" 로 바꾸는데, 이때 `JudgePanel.from_settings()` 의 키 로딩이 깨지면 → healthcheck 실패 → **Railway 재배포가 뜨지 않음.**
   - 반드시 §7 의 신규 회귀 항목으로 검증할 것.

2. **[배포 충돌 인지] 전 기능 ephemeral 의 배포 환경 의미.**
   - `_defaults`/`_history`/`topic_registry.json` 모두 컨테이너 파일시스템에 쓰인다. 배포 환경에서는 **재배포 시 소실**된다(방금 `runs/` 휘발로 인한 StaticFiles 404 와 동일 함정).
   - 즉 배포된 Vercel 화면에서 프롬프트 저장/키 입력/토픽 추가는 동작하나 재배포·재시작하면 빈 상태로 돌아간다. 이는 의도된 동작이며 v2 에서 Volume/DB 로 해소 예정.
   - RESULT.md 에 "배포 환경에서 admin 저장 기능은 ephemeral — 로컬 시연 권장" 명시.

---

## ▶ Claude Code 실행 명령 (복붙)

````text
docs/patches/2026-06-04_b3-s3-e_admin_persona_ops.md 를 읽고 B3-S3-E를 "자율 진행 모드"로 전부 구현해라.

규칙:
- 사용자는 부재 중이다. 질문하지 말고 명세 + 아래 자율 결정 권한 범위 안에서 끝까지 진행해라.
- 진짜로 막히는 항목만 [BLOCKED] 양식으로 로그에 남기고, 그 항목은 건너뛴 뒤 독립적인 다음 항목을 계속 진행해라. 절대 전체를 멈추지 마라.
- 기존 기능(트레이스 뷰어 C, Judge 시각화 D, generate 파이프라인, 라이브 SSE)이 깨지면 [REGRESSION] 양식으로 즉시 중단·해당 변경 롤백 후 로그.
- git add / commit 은 하지 마라. 작업만 완료하고 변경 파일 목록만 마지막에 보고해라.
- 작업 끝나면 명세 §6 종료조건 체크리스트를 실제 결과로 채워서 docs/patches/2026-06-04_b3-s3-e_RESULT.md 로 저장해라.

배포 환경 필수 회귀 (갱신본 §7 신규 2건 — 반드시 검증):
- A2 키 조회 경로 변경 후 /api/health 가 200 + judge_panel_available 정상 반환하는지 확인. JudgePanel.from_settings() 의 키 로딩을 깨면 Railway healthcheck 실패로 배포가 안 뜬다 → [REGRESSION] 즉시 롤백.
- 기존 backend/api/routers/prompts.py 라우터가 이미 존재한다. 새 /api/admin/prompts 와 경로·기능 중복되지 않게 하라. 중복이면 기존 것을 보강하고 신규 생성하지 마라.

먼저 §3 사전 인벤토리부터 실행해서 현재 구조를 파악한 뒤 그에 맞춰 작업해라.
````

---

## §0. 자율 진행 모드 — 보고 양식 / 권한

### 보고 양식 (로그 + 최종 RESULT.md 에 동일 기록)

```
[BLOCKED] <항목ID> : <한 줄 사유>
  - 시도: <무엇을 해봤나>
  - 필요: <어떤 결정/정보가 있어야 풀리나>
  → 이 항목만 건너뛰고 다음 독립 항목 진행함

[REGRESSION] <무엇> 깨짐 : <증상>
  → 원인 변경 롤백함 / 재발 방지: <조치>
```

### 자율 결정 권한 (질문 없이 진행 OK — 단 RESULT.md 에 1줄씩 기록)

- shadcn/ui v4 호환 조정, 더 나은 async/React 패턴, 명백한 타입·import 버그 수정
- 기존 컴포넌트·디자인 토큰 재사용 위한 경로/이름 조정
- 명세의 예상 경로가 실제와 다를 때 실제 경로에 맞춰 조정 (§3 인벤토리 결과 우선)

### 금지 (반드시 BLOCKED 보고 후 건너뛸 것)

- 새 외부 라이브러리 추가 (명세에 명시된 것 외)
- **영속성 도입** (DB·Railway Volume·외부 스토리지) — 이번 범위 아님. 전부 ephemeral 유지
- 새 페이지/기능을 명세 범위 밖으로 확장
- 기존 파이프라인·에이전트 로직 변경 (프롬프트 파일 내용은 사용자만 수정)
- **LLM 클라이언트 초기화 인자(grounding/response_mime_type) 변경** — A2 는 키 "조회" 만 바꾸고 클라이언트 생성 인자는 손대지 말 것

---

## §1. 목표 / 범위

운영자가 코드 없이 AIDEN을 다룰 수 있는 어드민 콘솔 완성. 4개 축:

1. **Persona Lab** — 9개 에이전트 system prompt 웹 편집 + 저장 + 기본값 복원 + 버전 히스토리(롤백)
2. **API 키 설정 (방안 A)** — 제공자별 키를 런타임 메모리에만 반영 (영속 X, 재시작 시 env 복귀)
3. **발행 이력 (Method A)** — 발행 토픽 레지스트리 CRUD + Topic Scout 프롬프트 주입 (중복 토픽 방지)
4. **운영 콘솔 셸** — `/admin` 레이아웃·사이드바·대시보드·운영 옵션 페이지

전부 **ephemeral**. 재배포 시 초기화는 의도된 동작이며 발표에서 한계점으로 명시 예정. 영속화는 v2.

---

## §2. 전제 / 현재 구조 가정 (self-contained)

> ⚠️ 아래는 **가정**이다. §3 인벤토리로 실제를 확인하고 다르면 실제에 맞춰라.
> **실측 확정분(2026-06-05 갱신)**: 백엔드 = `backend/api/` (FastAPI 진입점 `backend.api.main:app`). 라우터 = `backend/api/routers/{generate,runs,stream,judges,personas,prompts}.py` — **`prompts.py` 이미 존재**. 프롬프트 파일은 `backend/agents/` 하위로 추정(최상위 `agents/` 아님). 인벤토리로 정확 경로 확정할 것.

- 백엔드: FastAPI + asyncio SSE. SDK `google-genai 2.6.0`, 모델 `gemini-2.5-flash`.
- 프론트: Next.js 14 App Router + TS strict + Tailwind + shadcn/ui v4 + Recharts + React Query. 위치 `frontend/`. API base 는 `frontend/lib/api.ts` 의 `API_BASE`(= `process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"`).
- 에이전트 system prompt: `*.md` (01~09). PromptLoader + placeholder 치환 패턴 존재 (`{PLACEHOLDER}` 주입).
- 디자인 토큰 (기존 — **새로 만들지 말고 재사용**):
  ```
  --bg-primary:#0a0a0b; --bg-secondary:#131316; --bg-elevated:#1a1a1f;
  --border-subtle:#2a2a30; --text-primary:#f4f4f5; --text-secondary:#a1a1aa;
  --text-muted:#71717a; --accent-pink:#ff2e98; --accent-pink-soft:#ff2e9820;
  ```
  폰트: UI `Inter` / 코드 `JetBrains Mono` / 한글 본문 `Pretendard`. 9 에이전트 이모지·색상 토큰은 기존 트레이스 뷰어 코드에 정의됨 — 거기서 import.
- 키 우선순위 패턴: Judge 모델 해석의 **3단계 우선순위(UI override > env > config YAML)** 가 이미 있음. API 키도 같은 컨셉: **런타임 override > env**.

### LLM SDK 주의 (회귀 방지)

- `google-genai 2.6.0` 사용. 구 `google-generativeai` 아님.
- **Grounding + `response_mime_type='application/json'` 동시 사용 불가.** A2 키 변경 로직은 키 "조회"만 바꾸고 LLM 클라이언트 초기화 인자(grounding/json mode)는 절대 건드리지 말 것.
- **`/api/health` 의 `judge_panel_available` 판정이 `JudgePanel.from_settings()` 키 로딩에 의존한다.** A2 가 이 경로를 깨면 Railway healthcheck 실패 → 배포 마비. §7 신규 회귀로 검증.

---

## §3. 사전 인벤토리 (먼저 실행, 결과를 RESULT.md 상단에 기록)

다음을 확인하고 실제 경로·존재 여부를 표로 남겨라:

1. 백엔드 루트, FastAPI 진입점, 기존 admin 라우터 유무 — **특히 `backend/api/routers/prompts.py` 가 무엇을 노출하는지** (경로·메서드 전부 나열). 새 `/api/admin/prompts` 와 중복되면 보강 방향 결정.
2. 프롬프트 `.md` 실제 경로 + 9개 파일명(01~09) + PromptLoader 클래스 위치
3. LLM 클라이언트 초기화 코드 — 키를 어디서 읽나 (env 변수명 실제 확인). **`/api/health` → `judge_panel_available` 산출 경로 추적** (어느 함수가 키를 읽는지).
4. Topic Scout(01) 프롬프트에 placeholder 주입 지점 + 기존 placeholder 목록
5. 프론트 `app/admin/` 하위 기존 페이지 (runs/judges/cost/personas/settings 중 무엇이 이미 있나)
6. 발행 이력용 데이터 파일 기존 위치 유무 (`data/` 하위 등)
7. 기존 토스트/모달/테이블 shadcn 컴포넌트 import 경로

> 인벤토리 결과가 §2 가정과 다르면 **실제를 따른다.** 이미 구현된 페이지·엔드포인트는 **덮어쓰지 말고 보강**한다(idempotent).

---

## §4. 작업 항목

### Part A — 백엔드

#### A1. 프롬프트 read/write/restore/history

> ⚠️ 인벤토리 1번에서 기존 `prompts.py` 가 일부 기능을 이미 노출하면, **그것을 확장**하라. 새 admin 라우터를 따로 만들어 경로가 갈라지지 않게 할 것.

엔드포인트 (기존 prompts 라우터 확장 우선, 정말 없으면 `admin_router` 신설):

| 메서드 | 경로 | 동작 |
|---|---|---|
| GET | `/api/admin/prompts` | 9개 에이전트 메타(id, 이름, 이모지/색상 키, 파일경로, 수정시각) 목록 |
| GET | `/api/admin/prompts/{agent_id}` | 단일 프롬프트 raw 텍스트 |
| PUT | `/api/admin/prompts/{agent_id}` | 본문 텍스트로 `.md` 덮어쓰기. **저장 직전 현재 내용을 `_history` 백업** |
| POST | `/api/admin/prompts/{agent_id}/restore` | `_defaults` 스냅샷으로 복원 |
| GET | `/api/admin/prompts/{agent_id}/history` | 백업 타임스탬프 목록 |
| POST | `/api/admin/prompts/{agent_id}/rollback` | body: `{timestamp}` → 해당 백업으로 복원 (롤백 전 현재본도 history 백업) |

구현 메모:
- 최초 1회 부팅 시 `prompts/*.md` → `prompts/_defaults/*.md` 스냅샷 (이미 있으면 skip). restore 원본.
- 히스토리: `prompts/_history/{agent_id}/{YYYYMMDD_HHMMSS}.md`.
- `pathlib.Path`, UTF-8, `logging`. agent_id 화이트리스트 검증(01~09만) — 경로 traversal 차단.
- PUT 직후 PromptLoader 캐시 있으면 무효화 → 다음 run 에 새 프롬프트 반영.
- ⚠️ **ephemeral**: `_history`/`_defaults` 도 파일이라 재배포 시 소실. RESULT.md 명시.

#### A2. API 키 런타임 설정 (방안 A)

- 런타임 키 저장소: 프로세스 전역 싱글톤(`RuntimeKeyStore`) — 메모리 dict. **파일/env 안 씀.**
- LLM 클라이언트가 키 조회 시 **런타임 override > env** 순. (기존 Judge 3단계 우선순위와 동일 컨셉)
- ⚠️ **키 "조회"만 변경. 클라이언트 초기화 인자(grounding/response_mime_type)는 건드리지 말 것.** `JudgePanel.from_settings()` 의 키 로딩 경로를 깨면 `/api/health` healthcheck 가 실패해 배포가 마비된다 — §7 신규 회귀로 반드시 검증.

| 메서드 | 경로 | 동작 |
|---|---|---|
| GET | `/api/admin/keys` | 제공자별 상태: `{provider, source: "runtime"\|"env"\|"none", masked: "AIza…••••"}` |
| PUT | `/api/admin/keys` | body: `{provider, key}` → 런타임 저장소에 반영 |
| DELETE | `/api/admin/keys/{provider}` | 런타임 override 제거 → env로 복귀 |

보안 (필수):
- 응답에 **평문 키 절대 금지** — 마스킹만(앞 4 + `••••`).
- **키를 로그에 남기지 말 것.** `logging` 에 key 변수 직접 출력 금지.
- 재시작 시 런타임 키 소실 → env fallback. 의도된 동작이며 UI 안내.

#### A3. 발행 이력 레지스트리 (Method A)

- 데이터: `data/topic_registry.json` (인벤토리에서 기존 위치 확인되면 거기). 스키마:
  ```json
  {
    "id": "uuid",
    "topic": "string",
    "category": "food|ai_trend|safety|culture|free",
    "status": "published|rejected|expired",
    "published_at": "ISO8601",
    "expiry": "ISO8601|null",
    "rejected_similar_to": "string|null"
  }
  ```
  > 참고: 실제 generate enum 은 `food|ai-trend|safety|culture|custom` 이다. 레지스트리 category 값을 generate enum 과 맞출지 자체 스키마로 둘지는 자율 결정하되 RESULT.md 에 기록.

| 메서드 | 경로 | 동작 |
|---|---|---|
| GET | `/api/admin/registry` | 목록 (status·category 필터 쿼리 지원) |
| POST | `/api/admin/registry` | 추가 |
| PATCH | `/api/admin/registry/{id}` | status/expiry 변경 |
| DELETE | `/api/admin/registry/{id}` | 삭제 |

Topic Scout 주입 (핵심 — 실제 동작):
- Topic Scout(01) 프롬프트에 `{PUBLISHED_TOPICS}` placeholder 추가 (기존 placeholder 주입 패턴 그대로).
- 주입 내용: `status == "published"` 이고 (expiry null 또는 미래)인 토픽의 `topic` 리스트를 JSON으로.
- 의미: "아래 토픽은 이미 발행됨. 중복·유사 주제 회피하라." 문구 + 리스트.
- 주입은 **읽기 전용** — Scout 가 레지스트리를 쓰지 않음. 발행 확정은 운영자 수동 추가(이번 범위) 또는 v2 자동화.
- ⚠️ ephemeral: json 재배포 소실. RESULT.md 명시.

---

### Part B — 프론트 (Next.js admin)

> 전부 기존 디자인 토큰·shadcn/ui·Recharts 재사용. **새 라이브러리 금지.** Monaco Editor만 예외적으로 필요(B2) — 미설치 시 설치, 설치 실패하면 `<textarea>` + 등폭폰트로 폴백하고 [BLOCKED] 로그.

#### B0. `/admin` 레이아웃 + 사이드바

- 좌측 고정 사이드바 네비: 대시보드 / Persona Lab / 발행 이력 / API 키 / 운영 옵션 (+ 인벤토리에서 발견된 runs·judges·cost 있으면 연결).
- 활성 메뉴 하이라이트(브랜드 핑크), 다크모드 토큰.
- 기존 admin 레이아웃 있으면 메뉴 항목만 보강.

#### B1. `/admin` (대시보드 랜딩)

- 요약 카드 4: 에이전트 9 / 최근 run 수 / 발행 토픽 수 / 키 설정 상태(설정된 제공자 n개).
- 각 카드 클릭 → 해당 페이지. 빈 상태(empty state) 디자인 포함.

#### B2. `/admin/personas` (Persona Lab) ⭐ 핵심

- 좌 패널: 9개 에이전트 리스트 (이모지 + 색상 점 + 이름, 기존 캐릭터 토큰 import). 미저장 변경 있으면 dot 표시.
- 우 패널: **Monaco Editor** (markdown, 선택 에이전트 프롬프트). 다크 테마.
- 액션 바: `저장` / `기본값 복원` / `버전 히스토리`.
  - 저장 → PUT, 성공 토스트, 좌 패널 미저장 dot 제거.
  - 기본값 복원 → confirm 후 restore.
  - 버전 히스토리 → 우측 드로어: 타임스탬프 목록 + 각 항목 `이 버전으로 롤백`(confirm).
- 미저장 상태에서 다른 에이전트 클릭 시 경고 모달.
- 파라미터 슬라이더(까칠도 등): config/agents.yaml 연동 가능하면 실동작, 아니면 **cut**(BLOCKED 로그 후 생략). A/B 테스트 영역: **cut**(범위 외).

#### B3. `/admin/keys` (API 키 설정 — 보안상 별도 페이지)

- 제공자 행 3개: Gemini / OpenAI / Anthropic (실제 env 변수명은 A2 인벤토리 결과 따름).
- 각 행: 현재 상태 뱃지(`런타임 설정됨` 핑크 / `env 사용중` 회색 / `미설정` 빨강) + 마스킹 표시 + `password` 입력 + `적용`/`해제`.
- 상단 안내 배너 (필수 문구):
  > 입력한 키는 **현재 실행 중인 서버 메모리에만** 반영됩니다. 서버 재시작·재배포 시 사라지고 환경변수 값으로 돌아갑니다. (영속 저장은 v2 예정)
- 입력값을 화면에 다시 평문으로 띄우지 말 것.

#### B4. `/admin/registry` (발행 이력)

- 테이블: topic / category / status(색상 뱃지) / published_at / expiry / 액션.
- 상단: `+ 토픽 추가` 모달(topic, category, status, expiry optional).
- 행 액션: status 변경(드롭다운), 삭제(confirm).
- status·category 필터. 빈 상태 디자인.

#### B5. `/admin/settings` (운영 옵션)

- ✅ 실동작: `max_iter`(1/2/3), `SAFETY_MODE`(dry_run/normal), 비용 예산(월/일/run) — 백엔드 연동 가능한 것만. 연동 불가하면 해당 항목 [BLOCKED] 로그 후 비활성 표시.
- 🎨 장식(툴팁 `?` 포함): 캐시 TTL / 동시 실행 수 / 로그 레벨 / 그라운딩 ON·OFF(에이전트별) / Slack webhook / 자동 백업 주기 / JSON strict / Streaming 청크.
- 장식 항목은 토글 동작만 하고 실제 반영 안 함을 코드 주석에 명시.

---

## §5. 코드 표준

- Python 3.11+ 타입 힌트, `pathlib.Path`, UTF-8, `logging`(`print` 금지), EOL LF.
- TS strict. 서버 상태는 React Query. SSE/기존 패턴 유지.
- API 키·프롬프트 본문을 로그·URL 쿼리스트링에 절대 넣지 말 것.
- 에이전트 id·provider 명은 화이트리스트 검증.

---

## §6. 종료 조건 (RESULT.md 에 실제 결과로 채울 것)

### 백엔드
- [ ] `/api/admin/prompts` GET — 9개 메타 반환
- [ ] 기존 `prompts.py` 와 경로/기능 중복 없음 (보강 방식 확인)
- [ ] PUT 저장 → `_history` 백업 생성 확인
- [ ] restore → `_defaults` 내용으로 복원 확인
- [ ] rollback → 지정 타임스탬프 내용 복원 확인
- [ ] PUT 후 다음 run 에서 새 프롬프트 반영 (캐시 무효화 확인)
- [ ] `/api/admin/keys` PUT → GET 시 `source: "runtime"` + 마스킹 표시
- [ ] DELETE keys → `source: "env"` 복귀
- [ ] 키가 응답·로그 어디에도 평문 노출 안 됨 (grep로 확인)
- [ ] registry CRUD 4종 동작
- [ ] Topic Scout 프롬프트에 `{PUBLISHED_TOPICS}` 주입 → published 토픽만 들어가는지 확인
- [ ] 백엔드 기존 테스트 전부 PASS (개수 기록 — 직전 baseline 56건)

### 프론트
- [ ] `npm run build` PASS (경고만 OK, 에러 0)
- [ ] `/admin` 5개 메뉴 라우팅 동작
- [ ] Persona Lab: 9 에이전트 로드 → 편집 → 저장 토스트 → 히스토리 드로어 → 롤백 동작
- [ ] `/admin/keys`: 상태 뱃지·마스킹·적용/해제 동작, 안내 배너 노출
- [ ] `/admin/registry`: 추가·상태변경·삭제·필터 동작
- [ ] `/admin/settings`: 실동작 항목 연동, 장식 항목 토글

### 전체
- [ ] BLOCKED 항목 수 / 내용 기록
- [ ] 변경 파일 목록 기록 (git add 하지 말 것)

---

## §7. 회귀 점검 (하나라도 깨지면 [REGRESSION])

- [ ] `/` 메인 → generate 실행 정상
- [ ] 라이브 SSE 스트리밍 정상 (2026-06-04 픽스 유지 — setState updater 순수성 깨지 않았나)
- [ ] 트레이스 뷰어(C) 정상
- [ ] Judge 시각화(D): radar + 3-Model 카드 + 카운트업 정상
- [ ] 최종 콘텐츠 iframe 정상 (2026-06-05 final-html url = `/api/runs/{id}/output` 유지)
- [ ] LLM 클라이언트: Grounding + JSON 우회(옵션 B) 안 깨짐 — 키 주입 경로 변경이 초기화 인자 안 건드렸나
- [ ] 기존 admin 페이지(runs/judges/cost 있으면) 정상

### 🆕 배포 환경 필수 회귀 (2026-06-05 추가)
- [ ] **`/api/health` 200 + `judge_panel_available` 정상 반환** — A2 키 조회 경로 변경이 `JudgePanel.from_settings()` 의 키 로딩을 깨지 않았는지. **이게 깨지면 Railway healthcheck 실패로 배포가 안 뜬다 → [REGRESSION] 즉시 롤백.** (로컬에서 `python scripts/run_api_server.py --no-reload` 기동 후 `GET /api/health` 로 검증)
- [ ] **기존 `backend/api/routers/prompts.py` 와 신규 `/api/admin/prompts` 경로/기능 중복 없음** — 중복이면 기존 것 보강, 신규 라우터 생성 금지. RESULT.md 에 보강/신설 중 무엇을 했는지 기록.

---

## §8. 시각 임팩트 체크리스트 (admin도 발표 시연 대상)

- [ ] 디자인 토큰 100% 준수 (임의 색 하드코딩 0)
- [ ] 다크모드 일관, 브랜드 핑크 포인트
- [ ] Persona Lab Monaco 다크 테마 + 9 에이전트 색상 점으로 "캐릭터 운영" 느낌
- [ ] 저장/롤백/적용 시 토스트 + 마이크로 인터랙션(페이드·호버)
- [ ] 모든 페이지 empty state 디자인 (빈 화면 방치 금지)
- [ ] 상태 뱃지 색상 의미 일관(핑크=활성/런타임, 회색=기본/env, 빨강=미설정·rejected)
- [ ] 데스크탑 우선. 모바일은 깨지지만 않게(최소 대응)

---

## §9. 위험 / cut 라인

| 항목 | 처리 |
|---|---|
| 버전 히스토리·롤백 | 구현하되 **ephemeral** (재배포 소실). 시연·운영 단기엔 충분. 한계 명시 |
| 파라미터 슬라이더(까칠도 등) | yaml 연동 되면 실동작, 안 되면 **cut** |
| A/B 테스트 영역 | **cut** (범위 외) |
| settings 장식 항목 | 토글만, 실반영 X (주석 명시) |
| API 키 방안 A | 런타임만, 재시작 소실 (의도) |
| 전 항목 영속성 | v2. 이번엔 절대 DB/Volume 도입 안 함 |

시간 부족 시 우선순위: **A1·A2·B2·B3(필수) > B4·A3(발행 이력) > B0·B1·B5(셸·옵션) > 슬라이더·장식.**

---

## §10. 저장 + 커밋 안내

### 이 .md 저장 위치
다운로드한 파일을 `docs/patches/2026-06-04_b3-s3-e_admin_persona_ops.md` 에 저장.

### 커밋 (Claude Code는 commit 안 함 — 사용자 수동)

1) 변경 확인:
```bash
git status
```

2) 분할 stage·commit (백엔드 → 발행이력 → 프론트 순 권장. 실제 경로는 git status 보고 맞출 것):

```bash
# 1. 프롬프트/키 백엔드
git add backend/
git commit -m "feat(admin): prompt edit/restore/history API + runtime API key store (방안 A)"

# 2. 발행 이력 레지스트리 + Topic Scout 주입
git add data/ backend/agents/  # 실제 프롬프트·데이터 경로로
git commit -m "feat(registry): topic registry CRUD + Topic Scout PUBLISHED_TOPICS injection (Method A)"

# 3. 어드민 프론트
git add frontend/
git commit -m "feat(admin-ui): Persona Lab + API key page + registry + settings shell (B3-S3-E)"
```

3) push → Railway(백엔드 변경 시) + Vercel(프론트 변경 시) 자동 재배포.
   **push 후 반드시 `/api/health` 200 확인** — A2 변경이 healthcheck 를 깨지 않았는지 배포 환경에서 재검증.

> `_defaults`/`_history` 백업 폴더, `data/topic_registry.json` 은 시연용 데이터일 수 있으니 commit 여부는 `git status` 보고 판단. 불필요하면 `.gitignore` 에 `_history/`·`topic_registry.json` 추가 고려 (단 배포 환경에선 어차피 ephemeral).

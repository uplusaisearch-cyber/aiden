# AIDEN Output History 영속화 작업 명세 (SQLite + Railway Volume)

**작성일:** 2026-06-05
**대상:** 백엔드(SQLite 적재·API) + 프론트(히스토리 페이지·메인 카드)
**목적:** Railway 재배포 시 휘발되는 run 결과 문제 해결. **종료된 run의 결과만**(트레이스/대화 제외) 영속 저장소에 append → 히스토리 메뉴에서 리스트·미리보기·다운로드.
**핵심 제약:**
- **라이브 SSE 경로(`/run/[id]`, `useRunStream`, `stream.py`) 절대 무변경.** 트레이스 뷰어 안 건드림.
- 적재는 run **완료 시점 1회**(write_metadata 직후). 실시간 발행 없음.
- 신규 디자인 금지 — 기존 디자인 토큰·shadcn·다크모드·브랜드 핑크 `#ff2e98`·기존 iframe 컴포넌트 재사용.

---

## 0. 범위 밖 (보류)

- 전체 영속화(프롬프트·API키·진행 중 run·트레이스). 무겁고 위험 → v2.
- 본 작업은 "종료된 run **결과 레코드**만" 별도 영속 저장.

---

## 1. 배경 (조사 결과 요약)

| 항목 | 현황 |
|---|---|
| 메인 카드 소스 | `GET /api/runs?limit=5` → 백엔드 `runs.py` list_runs가 **디스크 `runs/` 폴더 스캔** → 재배포 시 휘발 |
| 메인 카드 cap | `recent-runs.tsx:48` `runs.slice(0,5)` (5건) |
| [전체보기] | `recent-runs.tsx:39-44` `<Link href="/admin/runs">` → **`/admin/runs` 미구현 = 404** |
| final_output.html | `run_manager.py:189-201` `result.get("final_html")` truthy일 때만 wrapper 입혀 저장. 부재/timeout/exception 시 미저장 |
| metadata.json | `run_manager.py:253-264` → `write_metadata()`. timeout/exception 시 미작성 |
| metadata["cost"] | `run_manager.py:205-251`. newsroom=실측 토큰(`is_actual_tokens=True`), **judge=추정(호출당 2000/1000 고정, `is_actual_tokens=False`)** |
| cost API 노출 | `routers/runs.py:73-92` `RunDetail.cost` |

→ 결과 레코드(점수·토큰·비용·HTML)는 metadata.json에 이미 모임. 이걸 **완료 시점에 SQLite로 한 번 더 떠서 영속**시키면 됨.

---

## 2. 저장소 — SQLite + Railway Volume

- DB: 단일 파일 `outputs.db`. 경로는 env `OUTPUTS_DB_PATH`로 주입.
  - 기본값(로컬 개발): `backend/.cache/outputs.db`
  - 배포(Railway): `/data/outputs.db` (Volume 마운트 경로)
- 드라이버: 파이썬 표준 `sqlite3`. ORM 불필요.
- **Railway Volume 마운트는 Kane이 콘솔에서 수동 설정**(아래 6장). 코드는 경로만 env로 받음.

### 스키마

```sql
CREATE TABLE IF NOT EXISTS outputs (
  run_id            TEXT PRIMARY KEY,
  topic             TEXT,
  category          TEXT,
  created_at        TEXT,     -- ISO8601
  weighted_score    REAL,
  scores_json       TEXT,     -- 육각형 축 점수 JSON (judge 5~6축)
  total_tokens      INTEGER,
  total_cost_usd    REAL,
  cost_is_estimated INTEGER,  -- 0/1. judge 추정 토큰 포함 시 1
  final_html        TEXT      -- 외부 wrapper 적용된 최종 HTML
);
CREATE INDEX IF NOT EXISTS idx_outputs_created_at ON outputs(created_at DESC);
```

- `run_id` PK → **UPSERT**(INSERT OR REPLACE)로 재실행/중복 적재 방지.
- `final_html`은 TEXT 컬럼 직접 저장(수십~수백 KB, SQLite TEXT 한도 내).

---

## 3. 백엔드 작업

### 3-1. 신규 모듈 `backend/storage/outputs_store.py`
- `init_db()` — 스키마 생성(앱 기동 시 1회 호출). idempotent.
- `upsert_output(record: dict) -> None` — UPSERT. 예외는 삼키고 `logging.error`만(적재 실패가 run을 깨면 안 됨).
- `list_outputs(limit: int, offset: int = 0) -> list[dict]` — **final_html 제외** 메타만 반환(페이로드 절감), created_at DESC.
- `get_output(run_id: str) -> dict | None` — final_html 포함 단건.
- 경로: `os.environ.get("OUTPUTS_DB_PATH", <기본값>)`, `pathlib.Path`, UTF-8.

### 3-2. 적재 훅 (`run_manager.py`)
- `write_metadata()` **직후** `upsert_output()` 호출.
- **적재 조건: 정상 종료 AND `final_html` truthy.** 둘 중 하나라도 불충족이면 적재 skip(빈 HTML 레코드 방지).
- 적재 데이터 소스:
  - topic·category·created_at·run_id: run 컨텍스트/metadata
  - weighted_score·scores_json: judge 결과(metadata에서)
  - total_tokens·total_cost_usd·cost_is_estimated: `metadata["cost"]`에서 (judge 추정 포함 여부로 `cost_is_estimated` 산정)
  - final_html: `run_manager.py:189-201`에서 저장한 그 wrapper 적용본(파일 또는 result 동일 소스)
- 적재 실패해도 run 결과/SSE에 영향 없도록 격리(try/except + log).

### 3-3. API 라우터 `backend/api/routers/outputs.py` (신규)
- `GET /api/outputs?limit=&offset=` → `list_outputs` (메타 리스트)
- `GET /api/outputs/{run_id}` → `get_output` (final_html 포함). 없으면 404.
- `GET /api/outputs/{run_id}/download` → `final_html`을 `text/html` + `Content-Disposition: attachment` 로 응답(또는 프론트 Blob 처리 — 둘 중 단순한 쪽, 아래 4-2 참조).
- 앱 기동 시 `init_db()` 등록.

### 3-4. 기존 `runs.py` 처리
- **건드리지 않음**(디스크 스캔 list_runs 그대로). 메인 카드 소스 전환은 프론트에서 `/api/outputs`로 변경(4-3). 트레이스 진입(`/run/[id]`)은 라이브/최근 run용으로 유지.

---

## 4. 프론트 작업

### 4-1. API 클라이언트 (`lib/api.ts`)
- `fetchOutputs(limit, offset)` → `GET /api/outputs`
- `fetchOutputDetail(runId)` → `GET /api/outputs/{id}`

### 4-2. 히스토리 페이지 `frontend/app/admin/runs/page.tsx` (신규)
- `GET /api/outputs` 리스트 표시: 토픽 · 카테고리 · 생성시간 · 종합점수 · 토큰 · 비용 · [미리보기] [다운로드].
- 비용 컬럼에 `cost_is_estimated=1`이면 "*추정 포함" 캡션/배지.
- 행 [미리보기] → `GET /api/outputs/{id}` → **기존 iframe 컴포넌트 재사용**으로 final_html 렌더(`srcDoc`).
- [다운로드] → final_html을 Blob(`text/html`)으로 묶어 `<topic>.html` 다운로드.
- 기존 admin 레이아웃/사이드바 슬롯에 자연스럽게 편입(keys/personas/registry/settings 와 동일 톤).
- **에이전트 대화/트레이스 미표시**(범위 밖).

### 4-3. 메인 카드 (`components/main/recent-runs.tsx`, `app/page.tsx`)
- 소스를 `fetchRecentRuns(5)` → `fetchOutputs(6)` 로 전환. cap `slice(0,5)` → `slice(0,6)`.
- 행 클릭 동작: **현재 동작을 먼저 읽고**, 트레이스(`/run/[id]`)로 가는 경우 트레이스 부재(재배포 후) 시 graceful 폴백(결과 미리보기로 보내거나 안내). 기존 클릭 동작이 결과 상세면 그대로.
- MOCK_RECENT_RUNS fallback은 유지하되 빈 DB일 때만 표시되도록.

### 4-4. [전체보기]
- href `/admin/runs` **그대로**(이제 실존). 라벨 "전체 보기 →" 유지(원하면 "전체 히스토리 →"로 — 선택, 사소).

---

## 5. 종료 조건

- `OUTPUTS_DB_PATH` env 미설정 시 기본값으로 동작, 설정 시 그 경로 사용.
- run 정상 종료 + final_html 존재 → `outputs.db`에 레코드 1건 적재(sqlite로 SELECT 확인). 실패/timeout run → 미적재.
- `GET /api/outputs` 200, 리스트 정상. `GET /api/outputs/{id}` final_html 포함.
- `/admin/runs` 렌더 + iframe 미리보기 + .html 다운로드 동작.
- 메인 카드 최대 6건, DB 소스.
- [전체보기] 클릭 → `/admin/runs` 정상(404 해소).
- `npm run build` PASS, 백엔드 import/기동 PASS.

## 6. 회귀 점검

- **라이브 generate → `/run/[id]` SSE 정상** — 메시지 누락/중복 없음(SSE 경로 무변경 확인). ← 최우선
- 기존 admin 페이지 4종(keys/personas/registry/settings) 정상.
- `runs.py` list_runs 무변경 확인.
- 적재 실패(예: DB 경로 권한 없음)가 run 완료/결과 응답을 깨지 않음(격리 확인).
- judge 비용 추정 레코드에 `cost_is_estimated=1` 정상 기록 + UI 캡션 노출.
- 기존 트레이스 뷰어·Judge 시각화 영향 0.

## 7. Railway Volume 영속 검증 (배포 핵심 — 수동 단계)

> 코드만으로는 영속 안 됨. Volume 마운트 + redeploy dry-run으로 실제 확인해야 함.

```
1. Railway 백엔드 서비스 → Volumes → 새 Volume 추가, Mount Path = /data
2. 서비스 Variables에 OUTPUTS_DB_PATH = /data/outputs.db 추가
3. 배포 후 run 1개 정상 종료시켜 적재
4. /admin/runs 리스트에 그 run 확인
5. Railway에서 redeploy 실행
6. /admin/runs 리스트에 그 run이 "그대로 남아있는지" 확인  ← PASS 시 영속 확정
```

- 2번 누락(env 미설정) 또는 Volume 미마운트 시 6번에서 소실 → 영속 실패.
- 배포 데모가 1순위이므로 이 검증은 마감 전 반드시 1회 통과.

## 8. 시각 임팩트 체크리스트 (`/admin/runs`)

- 리스트가 기존 admin 톤과 일관(폰트·간격·다크모드·핑크 액센트).
- 점수/토큰/비용 수치 정렬·단위 표기 명확(비용 `$`, 추정 배지).
- iframe 미리보기 = 실제 PlusTap 콘텐츠 룩 그대로(wrapper CSS 적용본).
- 빈 상태(레코드 0건) 안내 문구.
- "9에이전트+3판정단 1회 = 토큰 N / 약 $X" 가 한눈에 — 발표 정량 증거로 읽히게.

## 9. cut 라인 (시간 부족 시)

| 우선순위 | 항목 |
|---|---|
| 필수 | SQLite + 적재 훅 + `GET /api/outputs`(+/{id}) |
| 필수 | `/admin/runs` 리스트 + .html 다운로드 |
| 필수 | Volume 마운트 + redeploy 영속 검증 |
| 있으면 좋음 | iframe 미리보기(기존 컴포넌트 재사용이면 저렴 → 포함) |
| 있으면 좋음 | 메인 카드 DB 전환(6건) |
| **cut 후보** | iframe 미리보기 → 다운로드만으로 대체 가능 |
| **cut 후보** | 메인 카드 전환 → 기존 5건 디스크 스캔 유지(히스토리만 영속이어도 핵심 충족) |

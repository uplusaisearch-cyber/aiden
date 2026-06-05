# 2026-06-05 Run UI 정리 — 토글 제거 / ← 메인 좌상단 / Game-ifier 라벨

## 배경 / 목적

`run/[id]` 트레이스 뷰어 화면 UI 3건 정리.

- 디자인 토큰 · shadcn · 다크모드 · 브랜드 핑크 `#ff2e98` **그대로 사용. 신규 디자인 금지.**
- 백엔드 로직(파이프라인/트레이스/에이전트) **무관**. 변경은 프론트 + `personas.yaml` 라벨 1줄.
- 본 명세는 코드 수정 전 **각 항목 대상 파일을 먼저 읽고 라인 위치 재확인**(아래 라인 번호는 직전 분석 기준, shift 가능).

## 변경 대상 요약

| # | 대상 | 변경 | 파일 |
|---|---|---|---|
| 1 | 인스턴트/재생 토글 | 제거 | `frontend/components/run/PlaybackToggle.tsx`, `frontend/app/run/[id]/page.tsx`, `frontend/hooks/useRunStream.ts` |
| 2 | ← 메인 버튼 | 좌상단 이동 | `frontend/app/run/[id]/page.tsx` |
| 3 | Game-ifier 라벨 | "인터랙티브 빌더"로 변경 | `backend/config/personas.yaml` |

---

## 1. PlaybackToggle 제거

### 현황
- `PlaybackToggle.tsx` = "인스턴트 / 재생" segmented 토글. `setMode` → URL query `?playback=animate` set/delete만 수행.
- **`?playback=animate`를 읽어 동작을 바꾸는 코드가 없음** → 양쪽 모드 결과 동일(no-op). `useRunStream`도 무시.
- `page.tsx` 사용처(약 `:130`)에서 `disabled={!run.isHistorical}` → 라이브 run에선 비활성, 완료된 historical run에서만 클릭 가능 = **누르면 아무 일도 안 일어남 → 신뢰 손상**.

### 변경
1. `page.tsx` 헤더에서 `<PlaybackToggle ... />` 사용 라인 제거.
2. `page.tsx` 상단 `import PlaybackToggle ...` 제거.
3. `PlaybackToggle.tsx` 파일 삭제(다른 곳에서 import 없음 grep으로 먼저 확인 후 삭제).
4. `?playback` query를 읽거나 쓰는 잔재 전부 제거 — grep `playback` 으로 확인. 읽는 곳이 없으므로 쓰는 곳(토글)만 빠지면 query 자체가 죽음. 남은 참조 0으로 정리.
5. `useRunStream.ts:35` 근방 `playback` 관련 주석 제거.

### 제약
- 헤더 좌측의 run id / 상태 표시는 **유지**.
- replay(타이핑 시뮬) 실제 구현은 본 명세 범위 아님(별건 v2).

---

## 2. ← 메인 좌상단 이동

### 현황
- 정상 라우트의 `<Link href="/">← 메인</Link>` = `page.tsx` 헤더(`:119-138`) **우측**, `PlaybackToggle` 옆에 배치(`justify-between`의 우측 그룹). 시선 분산.
- 별개로 에러/폴백 화면의 ← 메인 4곳 존재: `page.tsx:64`(페르소나 로딩 실패), `page.tsx:99`(스트림 에러), `app/error.tsx:46`, `app/not-found.tsx:20`.

### 변경
- 정상 라우트의 ← 메인을 **화면 좌상단**으로 이동. 권장 배치: 3-컬럼 그리드(`:109` `grid-cols-[280px_1fr_320px]`) **상단에 슬림 풀폭 top bar 1줄** 추가, 그 **맨 좌측**에 ← 메인 left-align.
  - top bar는 단일 행, 작은 텍스트(기존 `text-[11px]` 톤), 배경 투명/기존 bg 매치, 하단 여백 최소.
  - 그리드 자체(컬럼 폭/스크롤)는 손대지 않음. top bar는 그리드 위에 additive.
- 가운데 헤더에서 ← 메인 **제거**(중복 금지). 가운데 헤더에는 run id / 상태만 남김 — 항목 1로 토글이 빠졌으므로 우측이 비면 정렬(좌측 정렬 등) 어색하지 않게 정리.

### 절대 건드리지 말 것
- 에러/폴백 ← 메인 4곳(`page.tsx:64`, `:99`, `error.tsx:46`, `not-found.tsx:20`)은 **그대로 유지**. 정상 라우트 헤더 건만 이동.

### 대안 (top bar가 레이아웃상 부자연스러우면)
- 좌측 컬럼(StagePanel 영역) 최상단 좌측에 ← 메인 배치. 단 컬럼 폭 280px에 끼어 답답하면 top bar안 우선. 어느 쪽이든 **아래 시각 체크리스트 통과**가 기준.

---

## 3. Game-ifier → "인터랙티브 빌더" (라벨만)

### 현황
- 표시 문자열 단일 출처: `backend/config/personas.yaml` → `stages.gameifier.display_name: "Game-ifier"`.
- 소비 경로: `/api/personas` → `frontend/lib/personas.ts::fetchPersonas` → `StagePanel.tsx:91 {meta.display_name}`.
- internal stage key `gameifier`는 별개로 5곳 하드코딩(yaml stages 키 + persona stage 2개 + `personas.ts:9` `StageKey` union + `StagePanel.tsx:19` `STAGE_ORDER`).

### 변경
- `personas.yaml`의 `stages.gameifier.display_name`을 **`"Game-ifier"` → `"인터랙티브 빌더"`** 로 1줄 변경.
- internal key `gameifier`는 **변경하지 않음**(5개 변경점 + 회귀 리스크 회피).

### 확인
- 프론트/백엔드에 `"Game-ifier"` 하드코딩 잔재 없는지 grep(`Game-ifier`, `Gameifier`, `게임`). 단일 출처가 맞으면 yaml 외 수정 불필요.

---

## 종료 조건

- **항목 1**: 코드베이스에 `PlaybackToggle` 참조 0, dead import 0, `playback` query 참조 0. `npm run build` PASS. 라이브 run / historical run 페이지 모두 정상 렌더(토글 없이).
- **항목 2**: ← 메인 좌상단 1곳 노출. 가운데 헤더에 ← 메인 없음. 에러/폴백 ← 메인 4곳 그대로. `npm run build` PASS.
- **항목 3**: `/api/personas` 응답의 `gameifier.display_name == "인터랙티브 빌더"`. StagePanel에 "인터랙티브 빌더" 표시. `"Game-ifier"` 하드코딩 잔재 0. `gameifier` key 불변.

## 회귀 점검

- `npm run build` PASS.
- **라이브 run**: SSE 스트림 정상 — 메시지 누락/중복 없음(직전 수정한 `appendUnique` / React Strict Mode 회귀 재발 없는지 확인).
- **historical run**: 정상 렌더(토글 제거 후 헤더 깨짐 없음).
- 3-컬럼 그리드 폭/스크롤 정상, 다크모드 정상.
- StagePanel stage 순서 · 색상 · 이모지 정상(`gameifier` key 유지 확인).
- `trace_converter` / `humanizer` 정상(key 미변경이라 영향 없음 — 확인만).
- 백엔드 personas 로드 정상, `/api/personas` 200.

## 시각 임팩트 체크리스트 (항목 2)

- ← 메인 좌상단 노출, 메인 복귀 동선 직관적.
- hover 시 브랜드 핑크 accent 등 기존 토큰 일관.
- 다크모드에서 대비 정상.
- 토글 제거 후 가운데 헤더 우측 빈 공간 어색하지 않게 정렬 정리됨.
- top bar 추가로 인한 콘텐츠 영역 세로 잠식/스크롤 이상 없음.

# AIDEN 토큰·비용 실측 집계 작업 명세 (B-안전 / 저장 전용)

**작성일:** 2026-06-05 (rev2)
**대상:** 백엔드(토큰·비용 실측 → run 종속 저장 + API 노출). **프론트는 라이브 UsageCard 제거만.**
**목적:** run당 실측 토큰·비용을 **결과물에 종속 저장**. 표시는 별도 히스토리 DB(다른 작업)에서 가져감.
**핵심 제약:** 라이브 SSE 경로 절대 무변경. cost_update 실시간 발행 안 함. 라이브 화면엔 토큰/비용 UI 노출 안 함.

---

## 1. 배경 (진단 결과)

- 토큰: `cost_tracker` 에 토큰 필드 부재 → UI 항상 0.
- 비용: UI 도달값은 Judge Panel 추정치 한 줄(`cost_usd_estimate`, 호출당 2000/1000 고정). 9 에이전트 비용은 `cost_tracker` 에 누적되나 UI 도달 경로 없음.
- 단가: gpt-5 / claude-opus-4-7 은 코드에 `# placeholder` 표기 — 실시세 미반영 가능.
- `cost_update` SSE: 프론트 listener 만 존재, 백엔드 미발행(dead listener).

**왜 SSE 안 쓰나:** 과거 `useRunStream` 의 비순수 setState updater + Strict Mode 이중호출로 messages 빈배열 reset 사고가 있었음. 마감 직전 그 경로 재오픈은 회귀 위험.

**이번 결정(rev2):** 라이브 표시는 **아예 포기**(UsageCard 제거). 토큰·비용은 run 결과물에 **종속 저장만** 하고, 표시는 별도 히스토리 DB 작업에서 그 필드를 읽어 처리. → 프론트 라이브 분기를 손대지 않으므로 SSE 회귀 표면 0.

---

## 2. 사전 확인 (수정 전 보고)

1. **토큰 실측 흐름:** `llm_clients.py` 의 `_call_gemini/_openai/_anthropic` 가 SDK 응답에서 usage(`usage_metadata.prompt_token_count`/`candidates_token_count`, OpenAI `usage.prompt_tokens`/`completion_tokens`, Anthropic `usage.input_tokens`/`output_tokens`)를 **이미 받고 있는지**, `estimate_cost` 로 넘기는지 확인. 토큰값이 흐르는 지점 특정. (이미 흐르면 작업 대폭 축소)
2. **cost_tracker 구조:** `record()` 인자, run 단위 누적 필드(`.cache/daily_cost.json` 구조). 토큰 필드 추가 위치.
3. **run 결과 저장 지점:** run 완료 시 `runs/<sid>/metadata.json`(또는 동등 파일)을 쓰는 코드 유무·위치. `RunDetail` 스키마(`schemas/run.py`)에 토큰/비용 필드 유무.
4. **라이브 UsageCard 위치:** `NowPlayingPanel.tsx` 의 UsageCard 렌더 라인, 그리고 그 카드가 의존하는 `run.totalTokens`/`run.totalCostUSD` 가 `useRunStream` 어디서 세팅되는지(라이브 onCostUpdate 리스너 :145-149 / history fetch :185,202).

> 위 4개 보고 후 코드 시작. 1번에서 토큰이 이미 흐르면 그대로 사용.

---

## 3. 작업 내용

### 3-1. 토큰 실측 추출 (llm_clients.py)
- 3사 SDK 응답에서 prompt/completion 토큰 실측 추출. 이미 추출 중이면 그대로 사용.
- 추출 실패/부재 시 0 폴백(예외로 run 중단 금지).

### 3-2. cost_tracker 토큰 누적
- `prompt_tokens`/`completion_tokens`(또는 `total_tokens`) 누적 필드 추가. `record()` 시 비용과 함께 토큰도 run 단위 누적.
- 기존 daily/monthly 누적·예산 `precheck()` 로직 **무변경**(필드 추가만).

### 3-3. run 종속 저장 (핵심 — 표시 아님, 저장만)
- run 완료 시 **run 결과물에 종속**되도록 `runs/<sid>/metadata.json` 에 `{ total_tokens, prompt_tokens, completion_tokens, total_cost_usd }`(9 에이전트 + Judge 합산) 저장. run_id 로 조회 가능해야 함.
- 이미 metadata 저장 코드가 있으면 필드 추가, 없으면 trace_logger/run_manager 완료 핸들러에 추가.
- **SSE publish 추가 금지.**

### 3-4. API 노출 (히스토리 DB가 어느 경로로 읽든 커버)
- `RunDetail` 스키마에 `total_tokens`/`total_cost_usd`(필요시 prompt/completion 분리) 추가, `GET /api/runs/{sid}` 가 metadata 에서 읽어 반환.
- 즉 **① 파일(runs/<sid>/metadata.json) + ② API(RunDetail) 둘 다** 노출 — 별도 히스토리 DB 작업이 파일을 읽든 API를 읽든 대응 가능하도록.
- 기존 `judge_panel.cost_usd_estimate` 는 두고, 전체 합산 실측치는 **별도 필드**로(혼동 방지).

### 3-5. 단가 교정
- `_PRICE_TABLE`/`_JUDGE_PRICE_TABLE` 의 `# placeholder` 단가(gpt-5, claude-opus-4-7) 확인 후 실시세 교정. **확실치 않으면 덮어쓰지 말고 "placeholder 잔존" 보고.**

### 3-6. 프론트 — 라이브 UsageCard 제거 (이것만)
- `NowPlayingPanel.tsx` 에서 **UsageCard 렌더 제거**(라이브 화면에 토큰/비용 노출 안 함).
- `useRunStream` 의 라이브 onCostUpdate 리스너가 UsageCard 전용이면 정리 가능하나, **상태 업데이트 로직·dedup·setState updater 는 손대지 말 것**(회귀 위험). 단순히 카드만 안 그리는 선에서 처리. 리스너 제거가 SSE 흐름에 영향 줄 소지 있으면 제거하지 말고 그대로 둘 것(dead 라도 무해).
- history fetch 분기 표시 로직은 **건드릴 필요 없음**(표시는 별도 히스토리 DB가 담당).

---

## 4. 종료 조건

- [ ] run 완료 후 `runs/<sid>/metadata.json` 에 실측 토큰(>0)·비용 저장.
- [ ] 비용이 9 에이전트 + Judge 합산 실측 기반.
- [ ] `RunDetail` 응답에 토큰/비용 필드 포함, run_id 로 조회 가능.
- [ ] 라이브 화면에 토큰/비용 UI 없음(UsageCard 제거).
- [ ] 단가 placeholder 교정 또는 잔존 사유 보고.

---

## 5. 회귀 점검 (SSE 보호 최우선)

- [ ] **stream.py 무변경, useRunStream 의 SSE 리스너·appendUnique·seenIds·setState updater 무변경**(과거 빈배열 reset 회귀 재발 방지).
- [ ] 라이브 run 정상 — "연결중..." 무한대기 재발 없음, 메시지 정상 스트리밍.
- [ ] UsageCard 제거가 NowPlayingPanel 레이아웃을 깨지 않음(빈 공간/정렬 확인).
- [ ] cost_tracker 의 예산 precheck/차단 로직 동일 동작.
- [ ] Judge Panel 점수·outlier·기존 cost_usd_estimate 무변경.
- [ ] 토큰 추출 실패 시에도 run 정상 완료(폴백 0).
- [ ] 백엔드 테스트 전건 PASS, npm build PASS.
- [ ] 과거 완료 run(토큰 필드 없는 metadata) 조회 시 크래시 없이 처리.

---

## 6. 검증 방법

- 실 LLM 1 run 완료 후 `runs/<sid>/metadata.json` 토큰>0·비용 확인.
- `GET /api/runs/{sid}` 응답에 토큰/비용 필드 확인.
- 라이브 화면에 UsageCard 안 뜨고, 스트리밍은 종전과 동일하게 흐르는지 육안 확인(회귀 없음).

---

## 7. commit 안내

```
git status
git diff --stat
```
백엔드 위주 단일 commit:
```
git add backend/core/llm_clients.py backend/core/cost_tracker.py backend/api/services/ backend/schemas/run.py backend/api/routers/runs.py frontend/components/run/NowPlayingPanel.tsx docs/patches/2026-06-05_token-cost-actuals.md
git commit -m "feat(cost): 토큰·비용 실측을 run에 종속 저장 + API 노출, 라이브 UsageCard 제거"
```
> 실제 변경 파일은 git status 로 보정. **stream.py / useRunStream 의 SSE 상태 로직이 diff 에 잡히면 잘못된 것 — 되돌릴 것.**

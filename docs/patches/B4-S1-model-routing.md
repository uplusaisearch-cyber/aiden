# B4-S1: 운영 경로에 에이전트별 모델 주입 (dead config 해소)

## 배경
- 운영 라이브(경로 A, `run_manager.py:238`)는 단일 `GeminiClient` 공유 → 9개 에이전트 전부 `DEFAULT_MODELS`(flash)로 도는 상태
- `config/agents.yaml`의 에이전트별 `model` 매핑(경로 B)은 dead config — yaml에 `gemini_pro`로 적혀 있어도 운영 경로가 안 읽음
- 목표: 경로 A가 에이전트별 모델을 받게 **최소 수정**. Newsroom 멀티프로바이더 전환 아님(Gemini 유지). 멀티프로바이더는 후속 B4-S2에서 별도 처리

## 목표 모델 배치 (마감용)
| 에이전트 | 모델 | 이유 |
|---|---|---|
| Trend Scout (01) | gemini-2.5-flash | grounding, 현행 유지 |
| Audience Analyst (02) | gemini-2.5-flash | 기계적 |
| Strategy Planner (03) | gemini-3.1-pro | 기획 품질 |
| Writer (04) | gemini-3.1-pro | 산문 생기 = 핵심 |
| Fact-Checker (05) | gemini-2.5-flash | grounding |
| Devil's Advocate (06) | gemini-2.5-flash | 비판 패턴, 유지 |
| Editor-in-Chief (07) | gemini-3.1-pro | Writer와 동일 등급 (Opus 차등은 cut) |
| Format Architect (08) | gemini-2.5-pro | 구조 정확도 |
| HTML Builder (09) | gemini-2.5-pro | 코드 정확도 |

> Writer/Editor만 3.1-pro로 분리하려면 `config/agents.yaml:8-12` 별칭에 `gemini_pro_hi` 추가. 안정 우선이면 전 pro 에이전트를 gemini-2.5-pro로 둬도 됨.

---

## 0. 선결 검증 (코드변경 X, 먼저 보고)
- `gemini-3.1-pro`가 google-genai 2.6.0 + 현재 API 키/티어(Tier1)에서 호출 가능한지 가벼운 호출 1회로 확인
- 불가 시 **BLOCKED 보고**하고 `gemini-2.5-pro` 폴백안 제시 후 대기

---

## 1. 작업 (선결 검증 OK 후, 커밋 3분할)

### Commit 1 — 에이전트별 모델 주입 배선
- `concrete_agents.py` / `run_manager.py:238` 경로에서 9개 에이전트가 동일 client 공유하던 구조를 **에이전트별 model 문자열을 받아 호출**하도록 변경
- 모델 출처는 `config/agents.yaml`의 `agents.*.model` 별칭 → 별칭 resolver(기존 `_resolve_model` 재사용 가능 여부 확인, 가능하면 재사용)
- env `AIDEN_GEMINI_MODELS` 등 기존 우선순위 체계와 충돌 안 나게 정리
- 별칭 미지정 에이전트는 기존 flash 유지 (안전 폴백)

### Commit 2 — 모델 배치 값 적용
- `config/agents.yaml` 별칭/매핑 정리:
  - planner / writer / editor → gemini-3.1-pro (또는 선결검증 폴백값)
  - architect / builder → gemini-2.5-pro
  - scout / audience / factcheck / advocate → gemini-2.5-flash
- Writer/Editor만 상위로 분리하고 싶으면 별칭 `gemini_pro_hi` 추가해 매핑

### Commit 3 — 프론트 / judge 모델 노출
- run 스트림 각 에이전트 단계에 사용 모델 라벨 표시 (config에서 주입, UI 하드코딩 금지)
- judge 카드에 judge 모델명(gemini-2.5-pro / gpt-5 / claude-opus-4-7) 표시
- 단가 placeholder 2곳(`llm_clients.py:97-98`, `judge_panel.py:37-38`) 동기화 여부만 **보고** (수정은 별도)

---

## 종료 조건
- [ ] run 로그상 9개 에이전트가 각자 지정 모델로 호출됨 (전부 flash 아님)
- [ ] Writer/Editor가 실제 pro 계열로 호출 (로그 모델명 확인)
- [ ] yaml의 agent별 model이 운영 경로에 실제 반영 (dead config 해소)
- [ ] run 화면에 에이전트별 모델 라벨 노출
- [ ] judge 카드에 judge 모델명 노출
- [ ] 백엔드 테스트 PASS, npm build PASS

## 회귀 점검
- [ ] grounding 쓰는 에이전트(scout/factcheck)에서 google_search 툴 정상 동작
- [ ] flash-lite 폴백 체인 유지
- [ ] JSON_FORCE_SUFFIX / grounding+JSON 우회 경로 영향 없음
- [ ] 기존 SSE 스트림 / pub-sub 정상
- [ ] pro 모델 전환으로 응답 지연·타임아웃 발생 안 함 (run 1회 완주 확인)

## 시각 임팩트 체크리스트
- [ ] 모델 라벨 카드 톤과 일치, 과하지 않게
- [ ] judge 카드 "모델별 점수" 한눈에 → 멀티프로바이더 교차검증 셀링 강화
- [ ] 모바일 380px 라벨 줄바꿈 / 잘림 없음

---

## 커밋 (자동 git add/commit 금지. 매 커밋 전 `git status` 확인 후 사용자가 직접 스테이징)

```
git status
git add <배선 변경 파일>
git commit -m "fix: route per-agent model in live pipeline (resolve dead config)"

git status
git add config/agents.yaml
git commit -m "feat: assign pro-tier models to planner/writer/editor"

git status
git add <프론트 파일>
git commit -m "feat: surface agent/judge model labels in UI"
```

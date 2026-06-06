# B4-S2: Writer=Claude Sonnet, Editor=Claude Opus (Anthropic 단일 프로바이더 추가)

## 모델 배치
| 에이전트 | 모델 | 프로바이더 |
|---|---|---|
| Trend Scout / Fact-Checker | gemini-2.5-flash (grounding) | Gemini, **고정** |
| Audience / Devil's Advocate | gemini-2.5-flash | Gemini |
| Strategy Planner | gemini-3.1-pro | Gemini |
| Format / HTML Builder | gemini-2.5-pro | Gemini |
| **Writer** | **claude-sonnet (최신)** | Anthropic |
| **Editor-in-Chief** | **claude-opus-4-7** | Anthropic |

> GPT/OpenAI는 안 씀. Writer Sonnet + Editor Opus 둘 다 Anthropic이라 **클라이언트 1개만 추가**하면 끝 → 작업·회귀 최소.
> 프로바이더 교차검증은 Judge Panel(Gemini+GPT+Claude)이 전담. Newsroom은 "Gemini 리서치 → Claude 작성 → Claude(상위) 검수"로 컨셉 명확화.

## 선행 조건
- B4-S1(에이전트별 모델 라우팅) 완료 상태에서 시작 — 에이전트별 모델 주입 배선 위에 Anthropic provider 분기만 추가
- 선결검증 불필요 (Judge Panel이 이미 claude-opus-4-7 호출 중 → Anthropic 클라이언트·키 검증됨)

## 범위 (엄수)
- 옮기는 에이전트: **Writer, Editor-in-Chief 2개만**
- Writer → Claude Sonnet(최신), Editor → claude-opus-4-7
- Gemini 고정(불변): Trend Scout, Fact-Checker (google_search grounding 의존)
- 나머지: Gemini 유지
- GPT/OpenAI 경로는 이번 패치에서 안 건드림 (Anthropic만 추가)

---

## 0. 사전 확인 (코드변경 X, 1줄 보고)
- Judge Panel이 쓰는 Anthropic 클라이언트(claude-opus-4-7 호출부) 위치 확인 → Writer/Editor에서 재사용 가능한지만 보고
- 사용할 Sonnet 모델 문자열 확정(현재 키로 호출되는 최신 Sonnet). 불확실하면 보고 후 대기

---

## 1. 작업 (커밋 2분할)

### Commit 1 — Writer/Editor Anthropic 분기 배선
- B4-S1에서 만든 "에이전트별 모델 주입" 지점에 provider 라우팅 추가
  - gemini_* → 기존 GeminiClient
  - anthropic_* → Judge가 쓰는 Anthropic 클라이언트 재사용
- provider별 응답 파싱 분기 (Gemini JSON 방식 ↔ Claude 출력 JSON 추출 차이 흡수)
- grounding 에이전트(scout/factcheck)는 분기 대상에서 제외하는 가드 추가
- 한 provider 호출 실패 시 run 전체가 죽지 않도록 에러 핸들링(명확한 에러 또는 폴백)

### Commit 2 — 모델 배치
- config/agents.yaml:
  - writer → anthropic 별칭 (claude-sonnet 최신)
  - editor → anthropic 별칭 (claude-opus-4-7)
  - 별칭 정의 섹션(agents.yaml:8-12)에 sonnet 별칭 없으면 추가
- 단가 placeholder도 provider별 실제값으로 갱신(가능 범위)

---

## 종료 조건
- [ ] Writer가 Claude Sonnet으로, Editor가 Claude Opus로 실제 호출됨 (run 로그 모델명 확인)
- [ ] Trend Scout/Fact-Checker는 여전히 Gemini + grounding 정상
- [ ] run 1회 E2E 완주, 산출물 정상 생성
- [ ] run 화면 라벨에 Writer=Claude Sonnet / Editor=Claude Opus 노출 (B4-S1 라벨 메커니즘 재사용)
- [ ] 백엔드 테스트 PASS, npm build PASS

## 회귀 점검
- [ ] grounding 에이전트 google_search 정상 (가드 동작 확인)
- [ ] Claude 출력 JSON 파싱 실패 0건 (Writer/Editor 파서 통과)
- [ ] JSON_FORCE_SUFFIX / grounding+JSON 우회 경로 영향 없음
- [ ] 타임아웃/지연 — run 1회 완주 시간 허용 범위 (Opus 검수 단계 지연 체크)
- [ ] SSE 스트림 / pub-sub 정상
- [ ] /admin/keys 런타임 키 override 경로와 충돌 없음
- [ ] B4-S1 모델 라우팅 + 토픽 다양화 패치와 충돌 없음
- [ ] Anthropic 호출 실패 시 run 전체 크래시 안 함

## 시각 임팩트 체크리스트
- [ ] run 화면에서 "Gemini 리서치 → Claude 작성 → Claude Opus 검수" 이종 협업이 라벨로 읽힘 (PT 핵심 컷)
- [ ] 모바일 380px 라벨 정상

---

## 커밋 (자동 git add/commit 금지. 매 커밋 전 `git status` 확인 후 사용자가 직접 스테이징)

```
git status
git add <provider 분기 배선 파일>
git commit -m "feat: add Anthropic provider routing for Writer/Editor"

git status
git add config/agents.yaml
git commit -m "feat: assign Claude Sonnet to Writer, Claude Opus to Editor"
```

---

## 마감 컷 기준
진행 중 아래 걸리면 **B4-S1 상태로 롤백, Claude 작성은 PT 로드맵으로**:
- Claude 출력 JSON 파싱이 기존 파서와 크게 안 맞아 흡수 작업이 큼
- run E2E 타임아웃 빈발 (Sonnet+Opus 2단계 지연)
- 6/7 밤까지 안정화 안 됨

B4-S1(전부 Gemini 계층형)만으로도 "flash 단일" 문제는 이미 해결됐으니, B4-S2는 글 품질 욕심분. 안전망 있으니 시도 가치 있음.

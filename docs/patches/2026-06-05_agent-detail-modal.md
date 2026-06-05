# AIDEN 에이전트 상세 모달 (iter 변천 뷰) 작업지시서

**작성일:** 2026-06-05
**대상:** 프론트엔드만 (Next.js 14 / shadcn/ui v4 / 기존 디자인 토큰)
**목적:** 트레이스 뷰어 버블 클릭 시, 해당 에이전트의 작성/지적/수정 내용과 iter 변천을 모달로 노출
**전제:** 데이터·API는 이미 보존됨(iter별 파일 + `ChatMessage.raw_json`). **백엔드 무변경.**

---

## 0. 실행 명령 (복사용)

```
이 파일을 docs/patches/2026-06-05_agent-detail-modal.md 로 저장한 뒤,
아래 지침대로 프론트엔드만 수정해줘.

[핵심]
- 기존 ChatStream.tsx 의 raw_json <pre> 펼침(L115-125)을 "에이전트 상세 모달" 로 교체.
- 같은 에이전트의 iter별 raw_json 을 모아 탭으로 보여주고,
  Writer/Fact-Checker/Devils/Editor 4종은 전용 렌더러, 나머지 5종은 공통 카드.
- 백엔드/스키마/personas/converter 는 절대 손대지 말 것.
- 새 디자인 잡지 말고 기존 디자인 토큰·shadcn 컴포넌트(Dialog/Tabs/Badge)를 그대로 사용.

작업 후 종료 조건 / 회귀 점검 / 시각 임팩트 체크리스트 표 출력.
git add / git commit 은 하지 말 것.
```

---

## 1. 사전 확인 (수정 전 보고)

1. **데이터 진입 경로:** `useRunStream` / `lib/api.ts` 의 `ChatMessage` 타입에서 `raw_json`·`iteration`·`agent`(또는 agent key) 필드가 어떻게 들어오는지 확인.
2. **iter 그룹핑 가능 여부:** 같은 에이전트의 iter1/2/3 메시지를 묶을 키(agent name + iteration)가 메시지에 있는지 확인. 없으면 그룹핑 로직을 어디서 만들지 보고.
3. **기존 모달 컴포넌트:** shadcn `Dialog` / `Tabs` / `Badge` 가 프로젝트에 이미 설치돼 있는지(`components/ui/`). 없으면 설치 대신 기존 패턴으로 대체.

> 위 3개 확인 후 코드 시작. iter 그룹핑 키가 없으면 그 부분만 알려줄 것.

---

## 2. 동작 명세

### 2-1. 진입점
- 트레이스 뷰어(ChatStream)의 **버블 클릭 → 모달 오픈**. 기존 `<pre>` 인라인 펼침 제거.
- 모달 헤더: 에이전트 이모지 + display_name + (iter 있으면) iter 탭.

### 2-2. iter 탭
- 클릭한 에이전트의 iter별 메시지를 모아 **탭(iter1 / iter2 / iter3)** 으로 전환.
- 단발 에이전트(iter 1개)는 탭 없이 단일 뷰.
- 탭 라벨에 핵심 지표 뱃지(예: Fact-Checker `confidence 7/10`, Devils `이슈 3건`) — 데이터 있으면.

### 2-3. 에이전트별 렌더러
| 에이전트 | 렌더러 | 모달 본문 |
|---|---|---|
| Writer | 전용 | 본문 전문(title/intro/sections[*].body/closing/cta) + revision_notes. **iter 간 본문 diff**(v1↔v2 변경 하이라이트) |
| Fact-Checker | 전용 | verification_log 항목별 카드, 상태 색 구분(verified=녹/ unverified=노랑/ corrected=빨강), confidence_score |
| Devils Advocate | 전용 | critical_issues 목록(problem → suggestion 쌍), severity 표시 |
| Editor | 전용 | accepted_critiques / rejected_critiques 2열 + 결정 사유(editorial_decision) |
| scout / analyst / planner / architect / builder | **공통 카드** | raw_json 을 key-value 카드로 렌더(중첩 객체는 접힘). iter 있으면 탭만 적용 |

### 2-4. diff 범위
- **텍스트 diff 는 Writer 본문에만** 적용(v1↔v2, v2↔v3 변경 부분 하이라이트).
- 나머지 에이전트는 iter 탭 전환으로 비교(diff 미적용).
- diff 라이브러리: 이미 설치된 게 있으면 사용, 없으면 가벼운 단어 단위 diff 직접 구현(무거운 의존성 추가 금지).

### 2-5. 폴백
- 전용 렌더러가 기대한 필드가 raw_json 에 없으면(스키마 변형) **공통 카드로 자동 폴백**. 깨지지 말 것.
- raw_json 자체가 비면 "원본 없음" 안내 + 기존 요약(humanized) 표시.

### 2-6. 범위 제외
- **Judge Panel 버블 제외.** 1 input→3 message 분할 구조라 이 모달 대상 아님. Judge 는 기존 B3-S3-D 시각화가 담당. 모달은 9 에이전트 버블에만.

---

## 3. 종료 조건

- [ ] 9 에이전트 버블 클릭 시 모달 오픈, iter 있으면 탭 전환 동작.
- [ ] Writer/Fact-Checker/Devils/Editor 전용 렌더러 4종 정상 표시.
- [ ] 나머지 5종 공통 카드 표시.
- [ ] Writer iter 본문 diff 동작(v1↔v2 변경 하이라이트).
- [ ] 필드 누락·raw_json 빈 경우 폴백 정상(크래시 0).
- [ ] Judge 버블은 모달 미적용(기존 동작 유지).
- [ ] 기존 디자인 토큰·shadcn 컴포넌트 사용, 새 색/폰트 추가 없음.

---

## 4. 회귀 점검

- [ ] **백엔드/스키마/personas/trace_converter 무변경** (프론트 파일만 diff).
- [ ] 기존 ChatStream 의 SSE 수신·메시지 push 로직 무변경 — 라이브 run 정상.
- [ ] `useRunStream` 의 appendUnique/seenIds 등 상태 로직 미터치 (과거 SSE 빈배열 회귀 재발 방지).
- [ ] 트레이스 뷰어 history fetch-then-stream 경로 정상.
- [ ] 모달 오픈/클로즈가 SSE 스트림이나 다른 탭(Judge 시각화/HTML iframe)에 영향 없음.
- [ ] npm build PASS.
- [ ] 무거운 신규 의존성 추가 없음(번들 사이즈 급증 방지).

---

## 5. 시각 임팩트 체크리스트

- [ ] Writer 모달에서 "v1 → v3 로 글이 실제로 고쳐진 흔적"이 한눈에 보임(diff 하이라이트).
- [ ] Fact-Checker 모달에서 unverified/corrected 항목이 색으로 즉시 구분됨 — "AI가 뭘 걸렀나" 직관적.
- [ ] Devils 모달에서 "이 부분이 약하다 → 이렇게 고쳐라" 가 쌍으로 읽힘.
- [ ] 모달 전환(탭/diff)이 부드럽고, 발표 화면에서 날것 JSON 이 아니라 정돈된 카드로 보임.
- [ ] 다크모드·브랜드 핑크 토큰과 톤 일관.

---

## 6. commit 안내

먼저 상태 확인:
```
git status
git diff --stat
```

단일 commit (프론트 단일 기능):
```
git add frontend/components/run/ <신규 모달/렌더러 컴포넌트 경로> frontend/lib/api.ts docs/patches/2026-06-05_agent-detail-modal.md
git commit -m "feat(frontend): 에이전트 상세 모달 — iter 변천·검증·수정 흔적 노출"
```
> 실제 변경 파일은 git status 로 확인 후 경로 보정. 백엔드 파일이 diff 에 잡히면 잘못된 것 — 되돌릴 것.
